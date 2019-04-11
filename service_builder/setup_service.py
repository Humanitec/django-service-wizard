import os

from django.core import management
from django.core.management.base import CommandError

from .utils import (PrettyPrint, replace_text, add_after_variable,
                    append_to_file, get_template_content, get_input, yes_or_no,
                    set_variable_value, yes_or_no_default)


def _welcome_msg():
    PrettyPrint.msg_blue('Welcome to Humanitec MicroService wizard!')
    PrettyPrint.print_green(r"""
  /\  /\_   _ _ __ ___   __ _ _ __ (_) |_ ___  ___
 / /_/ / | | | '_ ` _ \ / _` | '_ \| | __/ _ \/ __|
/ __  /| |_| | | | | | | (_| | | | | | ||  __/ (__
\/ /_/  \__,_|_| |_| |_|\__,_|_| |_|_|\__\___|\___|

    """)
    PrettyPrint.msg_blue('We will help you to set up a MicroService :)')


def _create_project(name: str):
    management.ManagementUtility(
        ['manage.py', 'startproject', name]).execute()
    PrettyPrint.msg_blue(
        'The Django project "{}" was successfully created'.format(name))


def _configure_project(name_project: str):
    # Add .gitignore
    content = get_template_content(os.path.join('gitignore', '.gitignore'))
    append_to_file(os.path.join(name_project, '.gitignore'), content)

    # Add requirements
    os.mkdir(os.path.join(name_project, 'requirements'))
    files_requirements = (
        os.path.join('requirements', 'base.txt'),
        os.path.join('requirements', 'production.txt'),
    )
    for file_requirements in files_requirements:
        content = get_template_content(file_requirements)
        append_to_file(os.path.join(name_project, file_requirements), content)

    # Create settings python module
    settings_dir = os.path.join(name_project, name_project, 'settings')
    os.mkdir(settings_dir)
    open(os.path.join(settings_dir, '__init__.py'), 'a').close()

    file_settings = os.path.join(settings_dir, 'base.py')
    os.rename(
        os.path.join(name_project, name_project, 'settings.py'),
        file_settings,
    )

    file_settings_production = os.path.join(settings_dir, 'production.py')
    open(file_settings_production, 'a').close()

    # Configure settings
    set_variable_value(file_settings, 'SECRET_KEY', "os.environ['SECRET_KEY']")
    replace_text(file_settings,
                 'DEBUG = True',
                 "DEBUG = False if os.getenv('DEBUG') == 'False' else True")
    replace_text(file_settings, 'INSTALLED_APPS', 'INSTALLED_APPS_DJANGO')

    content = get_template_content(os.path.join('settings',
                                                'base_installedapps.tpl'))
    add_after_variable(file_settings, 'INSTALLED_APPS_DJANGO', content)

    content = get_template_content(os.path.join('settings',
                                                'base_appended.tpl'))
    content = content.replace('{{ name_project }}', name_project)
    append_to_file(file_settings, content)

    content = get_template_content(os.path.join('settings', 'production.tpl'))
    append_to_file(file_settings_production, content)

    replace_text(
        file_settings,
        "STATIC_URL = '/static/'",
        "STATIC_URL = os.getenv('STATIC_URL', '/static/')"
    )

    # Configure databases
    replace_text(
        file_settings,
        "'ENGINE': 'django.db.backends.sqlite3'",
        "'ENGINE': 'django.db.backends.{}'.format(os.environ['DATABASE_ENGINE'])"  # noqa
    )
    replace_text(
        file_settings,
        "        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),",
        """\
        'NAME': os.environ['DATABASE_NAME'],
        'USER': os.environ['DATABASE_USER'],
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.environ['DATABASE_PORT'],\
""")

    # Modify wsgi.py and add Gunicorn conf
    file_gunicorn = os.path.join(name_project, name_project,
                                 'gunicorn_conf.py')
    content = get_template_content(os.path.join('conf', 'gunicorn_conf.py'))
    append_to_file(file_gunicorn, content)

    file_wsgi = os.path.join(name_project, name_project, 'wsgi.py')
    replace_text(file_wsgi,
                 '{}.settings'.format(name_project),
                 '{}.settings.production'.format(name_project))

    # Modify manage.py default Django settings
    file_manage_py = os.path.join(name_project, 'manage.py')
    replace_text(file_manage_py,
                 '{}.settings'.format(name_project),
                 '{}.settings.base'.format(name_project))

    # Modify urls.py
    urls_py = os.path.join(name_project, name_project, 'urls.py')
    replace_text(urls_py, 'from django.contrib import admin', """\
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns""")
    replace_text(urls_py,
                 'from django.urls import path',
                 'from django.urls import path, include')
    replace_text(urls_py,
                 ']',
                 """\
    path('health_check/', include('health_check.urls')),
]

urlpatterns += staticfiles_urlpatterns()
""")

    # Add README
    file_readme = os.path.join(name_project, 'README.md')
    content = get_template_content(os.path.join('readme', 'README.md'))
    content = content.replace('{{ name_project }}', name_project)
    append_to_file(file_readme, content)

    # Add permissions
    permissions = os.path.join(name_project, name_project, 'permissions.py')
    content = get_template_content('permissions.py')
    append_to_file(permissions, content)


def _configure_swagger(project_name, display_project_name, project_description):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Modify requirements
    append_to_file(os.path.join(base_dir, project_name, os.path.join('requirements', 'base.txt')), "drf-yasg==1.10.2")
    # Modify settings
    base_py = os.path.join(base_dir, project_name, project_name, 'settings', 'base.py')
    replace_text(base_py,
                 "'health_check.db',", """\
    'health_check.db',

    # openapi
    'drf_yasg',
""")
    # Modify urls.py
    urls_py = os.path.join(base_dir, project_name, project_name, 'urls.py')
    replace_text(urls_py,
                 'from django.urls import path, include', f"""\
from django.urls import path, include, re_path
from rest_framework import permissions


# openapi implementation
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

swagger_info = openapi.Info(
        title="{display_project_name}",
        default_version='latest',
        description="{project_description}",
)

schema_view = get_schema_view(
    swagger_info,
    public=True,
    permission_classes=(permissions.AllowAny,),
)
""")
    replace_text(urls_py,
                 "path('health_check/', include('health_check.urls')),",
                 """\
    re_path(r'^docs/swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('health_check/', include('health_check.urls')),
""")  # noqa


def _create_app(name_project: str, name_app: str):
    main_dir = os.getcwd()
    os.chdir(name_project)
    try:
        management.call_command('startapp', name_app)
    except CommandError:
        os.chdir(main_dir)
        raise
    else:
        PrettyPrint.msg_blue(
            'The app "{}" was successfully created'.format(name_app))

    # Add new app to settings
    file_settings = os.path.join(name_project, 'settings', 'base.py')
    replace_text(file_settings, '{{ name_app }}', name_app)


def _configure_docker(name_project: str):
    src_dest_list = (
        [os.path.join('docker', 'Dockerfile'), '.', 0o644],
        [os.path.join('docker', 'Dockerfile.nginx'), '.', 0o644],
        [os.path.join('docker', 'docker-compose.yml'), '.', 0o644],
        [os.path.join('docker', '.dockerignore'), '.', 0o644],
        [os.path.join('docker', 'docker-entrypoint.sh'), '.', 0o755],
        [os.path.join('docker', 'docker-entrypoint-dev.sh'), '.', 0o755],
        [os.path.join('scripts', 'run-collectstatic.sh'), 'scripts', 0o755],
        [os.path.join('scripts', 'run-tests.sh'), 'scripts', 0o755],
        [os.path.join('scripts', 'wait-for-it.sh'), 'scripts', 0o755],
    )
    for (src, dest, perm) in src_dest_list:
        if dest != '.' and not os.path.isdir(dest):
            os.mkdir(dest)
        content = get_template_content(src)
        content = content.replace('{{ name_project }}', name_project)
        append_to_file(
            os.path.join(dest, os.path.basename(src)),
            content, recreate=True, permission=perm)

    # Add README info
    file_readme = 'README.md'
    content = get_template_content(os.path.join('readme', 'docker.md'))
    content = content.replace('{{ name_project }}', name_project)
    append_to_file(file_readme, content)

    PrettyPrint.msg_blue('Docker support was successfully added')


def _configure_drone_ci():
    files_to_copy = [
        [os.path.join('requirements', 'ci.txt'),
         os.path.join('requirements', 'ci.txt'), 0o644],
        [os.path.join('drone-ci', '.flake8'), '.flake8', 0o644],
        [os.path.join('drone-ci', '.coveragerc'), '.coveragerc', 0o644],
        [os.path.join('drone-ci', '.drone.yml'), '.drone.yml', 0o644],
        [os.path.join('scripts', 'run-tests.sh'),
         os.path.join('scripts', 'run-tests.sh'), 0o755],
        [os.path.join('scripts', 'wait-for-it.sh'),
         os.path.join('scripts', 'wait-for-it.sh'), 0o775],
    ]

    for source, destination, permission in files_to_copy:
        append_to_file(
            filename=destination,
            text_to_append=get_template_content(source),
            recreate=True,
            permission=permission
        )

    PrettyPrint.msg_blue('Drone CI support was successfully added. Make sure '
                         'to configure the needed permissions in the Drone CI '
                         'web administration panel')


def _configure_docker_registry(name_project: str, registry_domain: str,
                               registry_folder: str):
    registry_url = os.path.join(registry_domain, registry_folder, name_project)
    filename = os.path.join('drone-ci', '.drone-appendix.yml')
    content = get_template_content(filename)
    content = content.replace('{{ registry_domain }}', registry_domain)
    content = content.replace('{{ registry_url }}', registry_url)
    append_to_file(filename='.drone.yml', text_to_append=content,
                   permission=0o644)


def setup():
    main_dir = os.getcwd()
    _welcome_msg()
    name_project = get_input(
        'Type in the name of your service (e.g.: appointments_service):')
    _create_project(name_project)
    _configure_project(name_project)
    name_app = get_input(
        'Type in the name of your application (e.g.: appointment):')
    _create_app(name_project, name_app)

    is_answer_yes_docker = yes_or_no('Add Docker support?')
    if is_answer_yes_docker:
        _configure_docker(name_project)

    is_answer_yes_drone = yes_or_no_default('Add Drone CI test support?', False)
    if is_answer_yes_drone:
        _configure_drone_ci()

    if is_answer_yes_docker and is_answer_yes_drone:
        is_answer_yes = yes_or_no(
            'Add Docker registry support to Drone?')
        if is_answer_yes:
            registry_domain = get_input(
                'Type in the domain of the registry (e.g.: registry.walhall.io):')
            registry_folder = get_input(
                'Type the folder of the registry (e.g.: humanitec):')
            _configure_docker_registry(name_project, registry_domain,
                                       registry_folder)

    is_answer_yes_swagger_docs = yes_or_no_default('Add Swagger docs?', True)
    if is_answer_yes_swagger_docs:
        display_project_name = get_input(
            'Type in the displayed Name of your service (e.g.: Appointment Service)'
        )
        project_description = get_input(
            'Type in the description of your service (e.g.: A microservice for saving and retrieving appointments.)'
        )
        _configure_swagger(name_project, display_project_name, project_description)

    PrettyPrint.msg_blue(
        'Great! Now you can find your new project inside the current\'s '
        'wizard folder with name "{}"'.format(name_project))
    os.chdir(main_dir)

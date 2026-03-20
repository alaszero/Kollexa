import os
import click
from app import create_app
from app.extensions import db

app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.cli.command('seed')
def seed_command():
    """Poblar base de datos con datos iniciales."""
    from scripts.seed import run_seed
    run_seed(app)


@app.cli.command('create-admin')
@click.option('--username', prompt=True)
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@click.option('--email', prompt=True)
def create_admin_command(username, password, email):
    """Crear un usuario administrador."""
    from scripts.seed import create_admin_user
    user = create_admin_user(username, password, email)
    if user:
        click.echo(f'Admin "{username}" creado exitosamente.')
    else:
        click.echo(f'Error: el usuario "{username}" ya existe.', err=True)


@app.cli.command('version')
def version_command():
    """Mostrar versión actual."""
    click.echo(f'Kollexa v{app.config["VERSION"]}')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

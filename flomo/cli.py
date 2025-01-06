import datetime
import sys
from typing import Tuple

import click
import click_aliases

import flomo.config as conf
import flomo.errors as errors
import flomo.helpers as helpers
import flomo.tracker as tracker
import flomo.ui as ui

# TODO: Use Pomodoro when starting and change to Flomodoro after 1 Session

class OrderCommands(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)


class MultiClass(click_aliases.ClickAliasedGroup, OrderCommands):
    pass


@click.group(cls=MultiClass)
def flomo():
    """
    A Flowmodoro CLI for productivity enthusiasts.
    """
    pass


@flomo.command(aliases=["i"])
def init():
    """
    Initialize the required files for Flomo.
    """
    db = tracker.Tracker(initializing=True)
    db.create_table()
    db.conn.close()

    conf.Config(initializing=True).create_config()


default_tag, default_name = conf.get_default_session_data()


@flomo.command(aliases=["s"])
@click.option(
    "-t",
    "--tag",
    help="Session Tag",
    default=default_tag,
)
@click.option(
    "-n",
    "--name",
    help="Session Name",
    default=default_name,
)
def start(tag: str, name: str):
    """
    Start a Flowmodoro session.
    """
    try:
        tag = tag.lower()
        if tag not in conf.Config().get_config(conf.TAG_COLORS):
            conf.Config().set_config(
                conf.TAG_COLORS, f"{tag} aquamarine3", nested_value=True
            )
        db = tracker.Tracker()
        db.create_table()
        session_id = db.create_session(tag, name, datetime.datetime.now())
        db.conn.close()
        ui.main(tag, name, session_id)
    except (
        errors.DBFileNotFoundError,
        errors.NoConfigError,
        errors.InvalidConfigKeyError,
        Exception,
    ) as e:
        helpers.error_log(f"{datetime.datetime.now()} - Error: {e}")
        print(e)
    finally:
        sys.exit()


@flomo.command(aliases=["t"])
def track():
    """
    Show the session history.
    """
    try:
        tracker.show_sessions()
    except (
        errors.DBFileNotFoundError,
        errors.NoSessionsError,
        errors.NoSessionError,
    ) as e:
        helpers.error_log(str(e))
        print(e)


@flomo.command(aliases=["d"])
@click.argument("session_ids", nargs=-1)
def delete(session_ids: Tuple):
    """
    Delete sessions.
    """
    try:
        db = tracker.Tracker()
        if not db.get_sessions():
            raise errors.NoSessionsError()
        session_1 = len(session_ids) == 1
        session_0 = len(session_ids) == 0
        click.confirm(
            f"Are you sure you want to delete the {f'session{'' if session_1 else 's'}: {", ".join(session_ids)}' if not session_0 else 'last session'}?",
            abort=True,
        )
        db.delete_session(session_ids)
        db.conn.close()
        if session_0:
            return print("Deleted the last session.")
        print(
            f"Deleted session{'' if session_1 else 's'}: {', '.join(map(str, session_ids))}"
        )
    except (
        errors.DBFileNotFoundError,
        errors.NoSessionError,
        errors.NoSessionsError,
    ) as e:
        helpers.error_log(str(e))
        print(e)


@flomo.command(aliases=["u"])
@click.argument("session_id")
@click.option("-t", "--tag", help="Session Tag")
@click.option("-n", "--name", help="Session Name")
def update(session_id: str, tag: str | None, name: str | None):
    """
    Update session data.
    """
    try:
        db = tracker.Tracker()
        db.update_session(session_id, tag, name)
        db.conn.close()
    except (
        errors.DBFileNotFoundError,
        errors.NoSessionError,
    ) as e:
        helpers.error_log(str(e))
        print(e)

@flomo.command(aliases=["x"])
@click.argument('file_path')
def export(file_path: str):
    """
    Export all sessions to a CSV file.

    Args:
        file_path (str): The file path where the CSV will be saved.
    """
    try:
        db = tracker.Tracker()
        db.export(file_path)
        db.conn.close()
        print(f"Exported sessions to {file_path}")
    except Exception as e:
        helpers.error_log(f"Export Error: {e}")
        print(f"Error exporting to CSV: {e}")


@flomo.command(aliases=["c"])
@click.option(
    "-n", "--notif", help="Set notification priority to 'off', 'normal', or 'high'."
)
@click.option("-tc", "--tag-color", help="Set or delete tag colors. (tag_name, color)")
@click.option("-ds", "--default-session", help="Set default session data. (tag, Name)")
def config(notif: str, tag_color: str, default_session: str):
    """
    Change the config values or get the config file path.
    """
    try:
        print(f"File Path: {helpers.get_path("config.json", True)}")
        conf_ = conf.Config()

        if notif:
            notif = notif.lower()
            if notif.lower() in ["off", "normal", "high"]:
                conf_.set_config(conf.NOTIFICATION_PRIORITY, notif)
                print(f"Notification Priority set to {notif}")
            else:
                raise click.BadOptionUsage("notif", "Invalid input")

        if tag_color:
            tag_color = tag_color.lower()
            tc = tag_color.split(" ")
            if len(tc) == 2:
                if not tc[1]:
                    raise click.BadOptionUsage("tag-color", "Invalid input")
                conf_.set_config(conf.TAG_COLORS, tag_color, nested_value=True)
                print(f"Tag {tc[0]}'s color set to '{tc[1]}'")
            elif len(tc) == 1:
                tag_colors = conf_.get_config(conf.TAG_COLORS)
                if not tc[0] in list(tag_colors.keys()):
                    raise click.BadOptionUsage("tag-color", "Invalid input")
                conf_.delete_tag_color(tc[0])
                print(f"Deleted color for tag '{tc[0]}'")
            else:
                raise click.BadOptionUsage("tag-color", "Invalid input")

        if default_session:
            ds = default_session.split(" ")
            ds[0] = ds[0].lower()
            if len(ds) == 2 and ds[0] and ds[1]:
                conf_.set_config(
                    conf.DEFAULT_SESSION_DATA, " ".join(ds), nested_value=True
                )
                print(f"Default Session Data set to Tag: {ds[0]} and Name: {ds[1]}")
            else:
                raise click.BadOptionUsage("default-session", "Invalid input")
    except errors.NoConfigError as e:
        helpers.error_log(str(e))
        print(e)


@flomo.command(aliases=["e"])
@click.option("-c", "--clear", is_flag=True, help="Clear the error log.")
def error(clear: bool):
    """
    Show the error log.
    """
    try:
        path = helpers.get_path("error.log", True)
        print(f"File Path: {path}")
        if clear:
            with open(path, "w") as f:
                f.write("")
            return print("Message log cleared.")

        with open(path, "r") as f:
            if not f.read():
                return print("No errors found till now.")
            print(f.read())
    except FileNotFoundError:
        print("No errors found till now.")


if __name__ == "__main__":
    flomo()

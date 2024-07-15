import datetime
import sqlite3

import click
import click_aliases

import flomo.tracker as tracker
import flomo.ui as ui


@click.group(cls=click_aliases.ClickAliasedGroup)
def flomo():
    """
    A Flowmodoro CLI for productivity enthusiasts.
    """
    pass


@flomo.command(aliases=["s"])
@click.option("-t", "--tag", default="Default", help="Session tag name.")
@click.option("-n", "--name", default="Work", help="Session Name")
def start(tag: str, name: str):
    """
    Start a Flowmodoro session.
    """
    db = tracker.Tracker()
    db.create_table()
    session_id = db.create_session(tag, name, datetime.datetime.now())
    db.conn.close()
    ui.main(tag.lower(), name, session_id)


@flomo.command(aliases=["t"])
def tracking():
    """
    Show the tracking history.
    """
    try:
        tracker.show_sessions()
    except sqlite3.OperationalError:
        print("No sessions were found.")


@flomo.command(aliases=["d"])
@click.argument("session_id")
def delete(session_id: str):
    """
    Delete a session.
    """
    db = tracker.Tracker()
    db.delete_session(float(session_id))
    db.conn.close()


if __name__ == "__main__":
    flomo()

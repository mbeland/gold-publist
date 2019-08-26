"""!pub <command> <arguments> is a publication tracking system

Commands:

* `new`: Someone published an article to be tracked

* `report`: List of publications by user or time

"""
import argparse
import datetime
import dateparser
import re
import urlmarker


def create_database(server):
    """Define the database used by this bot function"""
    server.query('''
        CREATE TABLE IF NOT EXISTS publist (
        author text,
        url text,
        pub integer)
    ''')


ARGPARSE = argparse.ArgumentParser()
ARGPARSE.add_argument('command', nargs=1)
ARGPARSE.add_argument('body', nargs='*')

MENTION_REGEX = "<@(|[WU].+?)>(.*)"
ROWID_REGEX = "[0-9]+$"


def add_pub(server, msg, body):
    author, body = parse_mentions(body)
    article = re.findall(urlmarker.URL_REGEX, body)
    server.query('''
            INSERT INTO publist(author, url, pub) VALUES (?, ?, ?)
        ''', author, article[0], int(datetime.datetime.now().strftime('%s')))
    rowid = server.query('''
            SELECT rowid FROM publist WHERE url = ?
        ''', article[0])
    return (f"Okay, tracking item {rowid[0][0]}, article by <@{author}> :tada:")


def report(server, msg, body):
    author, body_chopped = parse_mentions(body)
    if author is not None:
        items = get_ids(server, author, "author")
    else:
        body_chopped = body[10:]
        items = get_ids(server, body_chopped, "time")
    response = "Okay, I know about these:\n"
    nl = '\n'
    if items is not None:
        for item in items:
            item = str(item)[1:-2]
            responses = server.query('''
                SELECT author, url FROM publist WHERE rowid = ? 
            ''', int(item))
            list_item = f"{item} - <@{responses[0][0]}>: {responses[0][1]} {nl}"
            response = response + list_item
    else:
        response = "Sorry, couldn't find anything for that - try rephrasing."
    return response

def get_ids(server, ident, lookupType):
    if lookupType == "author":
        ids = server.query('''
            SELECT rowid FROM publist WHERE author = ?
            ''', ident)
    else:
        timeSet = (dateparser.parse(str(ident)))
        if timeSet is not None:
            timeSet = int(timeSet.strftime('%s'))
            ids = server.query('''
                SELECT rowid FROM publist WHERE pub >= ?
            ''', timeSet)
        else:
            ids = None
    return ids


def parse_mentions(body):
    """ Finds username mentions in message text and returns User ID"""
    user = re.search(MENTION_REGEX, body)
    return (user.group(1), user.group(2).strip()) if user else (None, None)


COMMANDS = {
    "new": add_pub,
    "report": report
}


def pub(server, msg, cmd, body):
    try:
        command_func = COMMANDS.get(cmd)
        return command_func(server, msg, body)
    except KeyError:
        return


def on_message(msg, server):
    create_database(server)

    text = msg.get("text", "")
    match = re.findall(r"!pub\s*(.*)", text)
    if not match:
        return

    # github.py: If given -h or -v, argparse will try to quit. Don't let it.
    try:
        ns = ARGPARSE.parse_args(match[0].split(' '))
    except SystemExit:
        return __doc__
    command = ns.command[0]

    # no arguments, print help
    if not len(command):
        return __doc__

    return pub(server, msg, command, msg["text"])

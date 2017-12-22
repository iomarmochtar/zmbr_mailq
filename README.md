Managing postfix's queue made easy.

This script is designed for Zimbra's postfix but still i made it independently for standalone postfix installation.

Background
==========

Sometime there are alot of email deffered in postfix's queue for a various reasons such as spam from hacked internal user,
junk messages from email blasting application, etc.

then i want to do an action, mass deleting by sender for example. because i don't to remember the combination command (postqueue, awk and postsuper) including their arguments so i must open the snippet command file (cheat sheet).

Then i make this script as a shortcut to do such things related to postfix's queue.

some features are inspired by [alexjurkiewicz's apq](https://github.com/alexjurkiewicz/apq)

FEATURES
=========

++Queue filtering by:++
- Queue ID
- Reason message (regex supported)
- Recipient (regex supported)
- Sender (regex supported)
- Exclude or Include active queue
- Size [TODO]
- Queue datetime [TODO]

++Actions:++
- Delete
- Requeue
- Hold
- Queue counting (can be combined by filtering)
- Show mail queue message

USING
=====

    usage: zmailq.py [-h] [-b BASE] [--mailq-data MAILQ_DATA] [--verbose]
                     [--action ACTION] [--reason REASON] [--recipient RECIPIENT]
                     [--sender SENDER] [--qid QID] [--exclude-active]
                     [--only-active] [--size SIZE]

    Zimbra MTA (Postfix) queue manager

    optional arguments:
      -h, --help            show this help message and exit
      -b BASE, --base BASE  Base path to find postfix queue binary file
      --mailq-data MAILQ_DATA
                            Use this file"s contents instead of calling mailq
      --verbose, -v         Verbosely show all executed command
      --action ACTION, -a ACTION
                            Action that will be applied

    search:
      Search patterns

      --reason REASON, -m REASON
                            Select messages with a reason matching this regex
      --recipient RECIPIENT, -r RECIPIENT
                            Select messages with a recipient matching this regex
      --sender SENDER, -s SENDER
                            Select messages with a sender matching this regex
      --qid QID, -q QID     Select messages with a queue ID match
      --exclude-active, -x  Exclude items in the queue that are active
      --only-active         Only include items in the queue that are active
      --size SIZE, -sz SIZE
                            Only include items in the queue that are active


#!/usr/bin/env python

import re
import datetime
import os
import sys
import subprocess
from pprint import pprint
from argparse import ArgumentParser


class ZMailQ_Err(Exception):
    pass


class ZMailQ(object):

    ACTION_DELETE = "delete"
    ACTION_REQUEUE = "requeue"

    __base_defaults = [
        "/opt/zimbra/postfix/sbin",
        "/opt/zimbra/common/sbin"
    ]
    queue_data = None
    cmds = {
        "postqueue": None,
        "postsuper": None
    }
    date_format = "%a %b %d %H:%M:%S"

    def __init__(self, base_path=None, queue_data=None, action=None, search_ptrn={}):
        self.search_ptrn = search_ptrn
        if queue_data:
            if not os.path.isfile(queue_data):
                raise ZMailQ_Err("Queue data (%s) doesn't exists"%(queue_data,))
            self.queue_data = queue_data

        if not self.queue_data and base_path:
            if not os.path.isdir(base_path):
                raise ZMailQ_Err("Folder %s doesn't exist" %(base_path,))
            self.__base_defaults.insert(0 , base_path)

        # check for base path
        if not self.queue_data:
            # must be ran as user root for user post* command
            if os.getuid() != 0:
                raise ZMailQ_Err("You must ran this as root")
            is_found = False
            for md in self.__base_defaults:
                if not os.path.isdir(md):
                    continue
                for cmd in self.cmds:
                    full_path = os.path.join(md, cmd)
                    if not os.path.isfile(full_path):
                        raise ZMailQ_Err("%s not found"%(full_path,))
                    self.cmds[cmd] = full_path
                    is_found = True
            if not is_found:
                raise ZMailQ_Err("Cannot find a valid path for commands: %s" % (",".join(self.cmds),))

    @property
    def lines(self):
        if self.queue_data:
            with open(self.queue_data, 'r') as f:
                return f.readlines()
        else:
            cmd = '%s -p'%(self.cmds['postqueue'],)
            output, error = subprocess.Popen(
                cmd, universal_newlines=True, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            if error:
                raise ZMailQ_Err("Error while executing command %s:%s"%(cmd, error))
            return output.splitlines()

    def process(self):
        re_qid = re.compile(
            r'^(?P<qid>[A-Z|\d|\*]+)\s+(?P<size>(\d+))\s+(?P<datetime>\w+\s\w+\s\d+\s+\d{2}:\d{2}:\d{2})\s+(?P<sender>.*?)$'
        )
        re_ignore_line = re.compile(r'^[\-Queue ID\-|\-\-]')
        re_cln = re.compile(r'(^\(|\)$)')
        ret = {}
        last_qid = None
        for line in self.lines:
            line = line.strip()
            if not line or re_ignore_line.search(line):
                continue
            s_qid = re_qid.search(line)
            if s_qid:
                result = s_qid.groupdict()
                result["is_active"] = False
                # if there is asterisk symbol in the end means it's still active
                if result["qid"][-1] == "*":
                    result["is_active"] = True
                    result["qid"] = result["qid"].replace("*", "")
                qid = result["qid"]
                last_qid = qid
                result["datetime"] = datetime.datetime.strptime(result["datetime"], self.date_format)
                result["size"] = int(result["size"])
                result["sender"] = result["sender"].lower()
                result["recipients"] = []
                ret[qid] = result
                continue
            # status msg
            if line.startswith("("):
                ret[last_qid]["recipients"].append(
                    (re_cln.sub("", line), [])
                )
                continue

            # recipients
            if len(line.split()) == 1:
                rec_last = len(ret[last_qid]['recipients'])
                if rec_last == 0:
                    ret[last_qid]["recipients"].append((None, []))

                ret[last_qid]["recipients"][rec_last-1][1].append(line.lower())
            else:
                raise ZMailQ_Err("Cannot parse this line: %s"%(line,))

        return ret

    def filter(self, parsed):
        """
        Filter result
        :param parsed:
        :return:
        """
        ptrn = self.search_ptrn
        # TODO: size, datetime
        for qid, x in parsed.items():

            if "qid" in ptrn and qid != ptrn["qid"]:
                continue

            if "sender" in ptrn and not re.search(ptrn["sender"], x["sender"]):
                continue

            if "only_active" in ptrn and not ptrn["active"]:
                continue
                
            if "exclude_active" in ptrn and ptrn["active"]:
                continue

            if "recipient" in ptrn or "reason" in ptrn:
                found = True
                for rec in x["recipients"]:
                    reason, recipients = rec
                    if "reason" in ptrn and not re.search(ptrn["reason"], reason):
                        found = False
                        break

                    if "recipient" in ptrn and not re.search(ptrn["recipient"], ",".join(recipients)):
                        found = False
                        break

                if not found:
                    continue
            yield x

    def main(self):
        parsed = self.process()
        for data in self.filter(parsed):
            pprint(data)


if __name__ == "__main__":

    def err_exit(msg, ret_code=1):
        sys.stderr.write("%s\n\n"%(msg,))
        sys.exit(ret_code)

    parser = ArgumentParser(description="Zimbra MTA (Postfix) queue manager")
    parser.add_argument("-b", "--base", default=None, help="Base path to find postfix queue binary file")
    parser.add_argument("--mailq-data", default=None, help="Use this file\"s contents instead of calling mailq")
    parser.add_argument("--count", "-c", action="store_true", help="Return only the count of matching items")

    ## SEARCH
    search = parser.add_argument_group("search", "Search patterns")
    search.add_argument("--reason", "-m", default=None, help="Select messages with a reason matching this regex")
    search.add_argument("--recipient", "-r", default=None, help="Select messages with a recipient matching this regex")
    search.add_argument("--sender", "-s", default=None, help="Select messages with a sender matching this regex")
    search.add_argument("--qid", "-q", default=None, help="Select messages with a queue ID match")
    search.add_argument("--exclude-active", "-x", action="store_true", help="Exclude items in the queue that are active")
    search.add_argument("--only-active", action="store_true", help="Only include items in the queue that are active")
    search.add_argument("--size", "-sz", default=None, help="Only include items in the queue that are active")

    ## ACTIONS
    action = parser.add_argument_group("action", "Action for matched queue mail")
    action.add_argument("--delete", "-d", action="store_true", help="Delete from queue")
    action.add_argument("--requeue", "-rq", action="store_true", help="Set to active queue")

    args = parser.parse_args()

    # print(args)
    base_path = None
    search_ptrn = {}

    if args.delete and args.requeue:
        err_exit("You can only choose wether delete or requeue for action argument !!!")

    search_args = ["reason", "recipient", "sender", "qid", "exclude_active", "only_active"]
    for sa in search_args:
        x = getattr(args, sa)
        if not x:
            continue
        search_ptrn[sa] = x

    ZMailQ(
        base_path=args.base,
        queue_data=args.mailq_data,
        search_ptrn=search_ptrn
    ).main()
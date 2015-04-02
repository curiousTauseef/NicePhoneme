#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.parse, urllib.request
import gzip, os, sys, io, json, time, re

# request data
request_info = """
:host:www.facebook.com
:method:POST
:path:/ajax/mercury/thread_info.php
:scheme:https
:version:HTTP/1.1
accept:*/*
accept-encoding:gzip, deflate
accept-language:en-US,en;q=0.8
content-length:316
content-type:application/x-www-form-urlencoded
cookie:STUFF
dnt:1
origin:https://www.facebook.com
referer:https://www.facebook.com/messages/conversation-STUFF
user-agent:STUFF
Form Data
view source
view URL encoded
messages[thread_fbids][STUFF][offset]:21
messages[thread_fbids][STUFF][limit]:20
:
client:web_messenger
__user:STUFF
__a:STUFF
__dyn:STUFF
__req:STUFF
fb_dtsg:STUFF
ttstamp:STUFF
__rev:STUFF
Name
Path
RANDOM OTHER STUFF HERE
"""

# session options
message_offset = 0
if len(sys.argv) > 1:
    try: message_offset = int(sys.argv[1], 0)
    except ValueError:
        print("Invalid message offset - message offset must be an integer", file=sys.stderr)
        sys.exit(1)

# find the request variables in the request data
match = re.search(r"^messages\[thread_fbids\]\[([^\]]+)", request_info, re.MULTILINE)
assert match is not None, "Cookie not found"
conversation_ID = match.group(1)
match = re.search(r"^cookie:(.*)", request_info, re.MULTILINE)
assert match is not None, "Cookie not found"
request_cookie = match.group(1)
match = re.search(r"^__user:(.*)", request_info, re.MULTILINE)
assert match is not None, "User ID not found"
request_user = match.group(1)
match = re.search(r"^__a:(.*)", request_info, re.MULTILINE)
assert match is not None, "Request __a value not found"
request_a = match.group(1)
match = re.search(r"^__dyn:(.*)", request_info, re.MULTILINE)
assert match is not None, "Request __dyn value not found"
request_dyn = match.group(1)
match = re.search(r"^__req:(.*)", request_info, re.MULTILINE)
assert match is not None, "Request __req value not found"
request_req = match.group(1)
match = re.search(r"^fb_dtsg:(.*)", request_info, re.MULTILINE)
assert match is not None, "Request fb_dtsg value not found"
request_fb_dtsg = match.group(1)
match = re.search(r"^ttstamp:(.*)", request_info, re.MULTILINE)
assert match is not None, "Request ttstamp value not found"
request_timestamp = match.group(1)
match = re.search(r"^__rev:(.*)", request_info, re.MULTILINE)
assert match is not None, "Request __rev value not found"
request_rev = match.group(1)

def get_messages(conversation_ID, message_offset = 0, messages_per_request = 2000):
    headers = {
        "origin": "https://www.facebook.com",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "accept-language": "en-US,en;q=0.8",
        "content-type": "application/x-www-form-urlencoded",
        "cookie": request_cookie,
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36",
        "accept": "*/*",
        "dnt": "1",
        "referer": "https://www.facebook.com/messages/conversation-" + conversation_ID,
    }
    try:
        while True:
            print("Getting messages {}-{}".format(message_offset, messages_per_request + message_offset), file=sys.stderr)
            
            form_data = urllib.parse.urlencode({
                "messages[thread_fbids][" + conversation_ID + "][offset]": str(message_offset), 
                "messages[thread_fbids][" + conversation_ID + "][limit]": str(messages_per_request), 
                "client": "web_messenger",
                "__user": request_user,
                "__a": request_a,
                "__dyn": request_dyn,
                "__req": request_req,
                "fb_dtsg": request_fb_dtsg,
                "ttstamp": request_timestamp,
                "__rev": request_rev,
            }).encode("UTF-8")
            request = urllib.request.Request("https://www.facebook.com/ajax/mercury/thread_info.php", form_data, headers)
            response_value = urllib.request.urlopen(request).read() # read the GZIP-compressed response value
            messages_data = gzip.GzipFile(fileobj=io.BytesIO(response_value)).read().decode("UTF-8") # GZIP-decompress the response value
            
            messages_data = messages_data[9:] # remove the weird code header at the beginning
            if "\"payload\":{\"end_of_history\"" in messages_data: # end of history, stop downloading
                break
            try:
                json_data = json.loads(messages_data)
                current_messages = json_data["payload"]["actions"] # messages sorted ascending by timestamp
                yield list(reversed(current_messages))
            except:
                print("Error retrieving messages. Retrying in 20 seconds. Data:", file=sys.stderr)
                print(messages_data, file=sys.stderr)
                time.sleep(20)
                continue
            message_offset += messages_per_request
            time.sleep(5)
    except KeyboardInterrupt: pass # stop when user interrupts the download

if __name__ == "__main__":
    sys.stdout.write("[\n")
    try:
        first = True
        for chunk in get_messages(conversation_ID, message_offset):
            for message in chunk:
                if first: first = False
                else: sys.stdout.write(",\n")
                sys.stdout.write(json.dumps(message, sort_keys=True))
    except KeyboardInterrupt: pass # keyboard interrupt received, close brackets in JSON output
    sys.stdout.write("\n]")
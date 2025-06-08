from llama_cpp import Llama
from llama_cpp.llama_chat_format import NanoLlavaChatHandler
from llama_cpp import LlamaGrammar
from llama_cpp.llama_grammar import json_schema_to_gbnf
from imaplib import IMAP4, IMAP4_SSL
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import html2text
from bs4 import BeautifulSoup
import markdown
import json
import os

prompt = """
"""

schema={
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "destination_address": {
      "type": "string"
    },
    "response_body": {
      "type": "string"
    }
  },
  "required": [
    "destination_address",
    "response_body"
  ]
}

# You can swap any model you like in here -- be sure to check licensing before you use them!
model = Llama.from_pretrained(
    repo_id="bartowski/c4ai-command-r7b-12-2024-GGUF",
    filename="c4ai-command-r7b-12-2024-Q4_K_L.gguf",
    verbose=False,
    n_ctx=4096,
    flash_attn=True,
)

def get_email_body(msg):    
    # Extract the email body
    if msg.is_multipart():
        for part in msg.iter_parts():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                return part.get_content()
            elif content_type == "text/html":
                html_content = part.get_content()
                h = html2text.HTML2Text()
                h.ignore_links = True  # You can adjust these options as needed
                h.ignore_images = True
                return h.handle(html_content)
    else:
        if msg.get_content_type() == "text/plain":
            return msg.get_content()
        elif msg.get_content_type() == "text/html":
            html_content = msg.get_content()
            h = html2text.HTML2Text()
            h.ignore_links = True  # You can adjust these options as needed
            h.ignore_images = True
            return h.handle(html_content)

def prepend_email_body(msg, new_text):
    # Determine the email body type

    new_msg = MIMEMultipart()
    new_msg['Subject'] = msg["subject"]
    new_msg['From'] = os.environ["AGENT_IMAP_EMAIL"]
    new_msg['To'] = msg["to"]
    new_msg['Time'] = msg["time"]
    #html_content = msg.get_content()
    #body = BeautifulSoup(html_content,features="lxml")
    new_html = markdown.markdown(new_text)
    new_body = BeautifulSoup(new_html,features="lxml")
    new_body.append(new_body.new_tag("hr"))
    new_body.append(new_body.new_tag("div", string="Original Message:"))
    #new_body.append(new_body.new_tag("div", string=f"Email UID: {num}"))
    new_body.append(new_body.new_tag("div", string=f"Subject: {msg['subject']}"))
    new_body.append(new_body.new_tag("div", string=f"From: {msg['from']}"))
    new_body.append(new_body.new_tag("div", string=f"To: {msg['to']}"))
    new_body.append(new_body.new_tag("div", string=f"Date: {msg['date']}"))
    #new_body.append(new_body.new_tag("p"))
    #new_body.append(body)
#    part1 = MIMEText(new_body.get_text(), 'plain')
    part2 = MIMEText(str(new_body), 'html')
#    new_msg.attach(part1)
    new_msg.attach(part2)
    new_msg.attach(msg)
    return new_msg

def write_email(imap, mail, folder):
    # Move the email to the specified folder
    message_bytes = mail.as_bytes()
    return imap.append(folder, "", mail["Time"], message_bytes)

gbnf = json_schema_to_gbnf(json.dumps(schema))
grammar = LlamaGrammar.from_string(gbnf)
messages = [
    {
        "role": "system",
        "content": "You are an email processing agent."
    }
]

with IMAP4(host=os.environ["AGENT_IMAP_HOST"], port = int(os.environ["AGENT_IMAP_PORT"])) as M:
    M.starttls()
    M.login(os.environ["AGENT_IMAP_USER"], os.environ["AGENT_IMAP_PASS"])
    M.select(mailbox='INBOX')
    typ, message_ids = M.search(None, 'ALL')
    for num in message_ids[0].split():
        local_messages = messages.copy()
        typ, data = M.fetch(num, '(RFC822)')
        msg = BytesParser(policy=policy.default).parsebytes(data[0][1])
        email_body = get_email_body(msg)

        assembled_body = f"""Subject: {msg['subject']}
From: {msg['from']}
To: {msg['to']}
TIME: {msg['Time']}

{email_body}
"""

        prompt = f"""{assembled_body}

Given the preceding email, generate a JSON object that contains the following fields:

"destination_address" will contain the fully-qualified email address to which the email should be routed.
"response_body" will contain any text that should precede the forwarded email body. You can use Markdown for formatting if necessary.

The rules for routing are as follows:

* Mail regarding the martial arts should be routed back to the originator, indcating that the dojo is closed for the summer.
* Advertisments and scams should be routed to deepsix@handshape.com
* All other mail should be routed to handshape@handshape.com. For these cases, include a one-line summary of the email body.

There is no need to quote the original email in your response.
"""
        local_messages.append(    
            {
                "role": "user",
                "content": prompt
            }
            )
        model_result = json.loads(model.create_chat_completion(
            messages=local_messages,
            grammar=grammar
        )['choices'][0]['message']['content'])
        new_msg = prepend_email_body(msg, model_result["response_body"])
        result = write_email(M, new_msg, 'Drafts')
        #if result[0] == 'OK':
        #    M.store(num, '+FLAGS', '\\Deleted')
        #    M.expunge()
        #else:
        #    print(result)
        #    print(f"Failed to move email with UID {num}")
    M.close()
    M.logout()

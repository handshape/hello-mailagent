# hello-mailagent
A proof-of-feasibility for an LLM-guided work router that preserves human agency.

None of this code has been inspected or approved by any governance body. 

# Required python libs
* llama-cpp-python
* html2text
* bs4
* markdown

Environment variables to set:
* AGENT_IMAP_USER - the username to use when logging into the IMAP server
* AGENT_IMAP_PASS - the password to use when logging in.
* AGENT_IMAP_HOST - the hostname or IP address of the IMAP server
* AGENT_IMAP_PORT - the port number to connect to - typically 143
* AGENT_IMAP_EMAIL - the email address of the agent being represented
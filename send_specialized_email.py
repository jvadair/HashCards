from registrationAPI import sendmail
from pyntree import Node

preregistered = Node('db/preregistered.pyn')

for email in preregistered._values:
    sendmail.send_template('email/special/early_access.html', "You've got early access to HashCards!",
                           email, email=email)

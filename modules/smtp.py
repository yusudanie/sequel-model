# SMTP module for the meshing-around bot
# 2024 Idea and code bits from https://github.com/tremmert81
# https://avtech.com/articles/138/list-of-email-to-sms-addresses/
# 2024 Kelly Keeton K7MHI

from modules.log import *
import pickle
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# System variables
trap_list_smtp = ("email:", "setemail:", "sms:", "setsms:", "clearsms:")
smtpThrottle = {}

if enableImap:
    # Import IMAP library
    import imaplib
    import email

# Send email
def send_email(to_email, message, nodeID=0):
    global smtpThrottle

    # throttle email to prevent abuse
    if to_email in smtpThrottle:
        if smtpThrottle[to_email] > time.time() - 120:
            logger.warning("System: Email throttled for " + to_email[:-6])
            return "⛔️Email throttled, try again later"
    smtpThrottle[to_email] = time.time()

    # check if email is in the ban list
    if nodeID in bbs_ban_list:
        logger.warning("System: Email blocked for " + nodeID)
        return "⛔️Email throttled, try again later"

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = EMAIL_SUBJECT
        msg.attach(MIMEText(message, 'plain'))

        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Send email
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        server.quit()

        logger.info("System: Email sent to: " + to_email[:-6])
    except Exception as e:
        logger.warning("System: Failed to send email: " + str(e))
        return False
    return True

def check_email(nodeID, sysop=False):
    if not enableImap:
        return

    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USERNAME, IMAP_PASSWORD)
        mail.select(IMAP_FOLDER)

        # Search for new emails
        status, data = mail.search(None, 'UNSEEN')
        if status == 'OK':
            for num in data[0].split():
                status, data = mail.fetch(num, '(RFC822)')
                if status == 'OK':
                    email_message = email.message_from_bytes(data[0][1])
                    email_from = email_message['from']
                    email_subject = email_message['subject']
                    email_body = ""

                    if not sysop:
                        # Check if email is whitelisted by particpant in the mesh
                        for address in sms_db[nodeID]:
                            if address in email_from:
                                email_body = email_message.get_payload()
                                logger.info("System: Email received from: " + email_from[:-6] + " for " + nodeID)
                                return email_body.strip()
                    else:
                        # Check if email is from sysop
                        for address in sysopEmails:
                            if address in email_from:
                                email_body = email_message.get_payload()
                                logger.info("System: SysOp Email received from: " + email_from[:-6] + " for sysop")
                                return email_body.strip()
                        
    except Exception as e:
        logger.warning("System: Failed to check email: " + str(e))
        return False

# initalize email db
email_db = {}
try:
    with open('data/email_db.pickle', 'rb') as f:
        email_db = pickle.load(f)
except:
    logger.warning("System: Email db not found, creating a new one")
    with open('data/email_db.pickle', 'wb') as f:
        pickle.dump(email_db, f)

def store_email(nodeID, email):
    global email_db

    # if not in db, add it
    logger.debug("System: Setting E-Mail for " + nodeID)
    email_db[nodeID] = email

    # save to a pickle for persistence, this is a simple db, be mindful of risk
    with open('data/email_db.pickle', 'wb') as f:
        pickle.dump(email_db, f)
    f.close()
    return True


# initalize SMS db
sms_db = [{'nodeID': 0, 'sms':[]}]
try:
    with open('data/sms_db.pickle', 'rb') as f:
        sms_db = pickle.load(f)
except:
    logger.warning("System: SMS db not found, creating a new one")
    with open('data/sms_db.pickle', 'wb') as f:
        pickle.dump(sms_db, f)

def store_sms(nodeID, sms):
    global sms_db
    try:
        logger.debug("System: Setting SMS for " + str(nodeID))
        # if not in db, add it
        if nodeID not in sms_db:
            sms_db.append({'nodeID': nodeID, 'sms': sms})
        else:
            # if in db, update it
            for item in sms_db:
                if item['nodeID'] == nodeID:
                    item['sms'].append(sms)

        # save to a pickle for persistence, this is a simple db, be mindful of risk
        with open('data/sms_db.pickle', 'wb') as f:
            pickle.dump(sms_db, f)
        f.close()
        return True
    except Exception as e:
        logger.warning("System: Failed to store SMS: " + str(e))
        return False

def handle_sms(nodeID, message):
    global sms_db
    # if clearsms, remove all sms for node
    if message.lower().startswith("clearsms:"):
        if any(item['nodeID'] == nodeID for item in sms_db):
            # remove record from db for nodeID
            sms_db = [item for item in sms_db if item['nodeID'] != nodeID]
            # update the pickle
            with open('data/sms_db.pickle', 'wb') as f:
                pickle.dump(sms_db, f)
            f.close()
            return "📲 address cleared"
        return "📲No address to clear"
    
    # send SMS to SMS in db. if none ask for one
    if message.lower().startswith("setsms:"):
        message = message.split(" ", 1)
        if len(message[1]) < 5:
            return "?📲setsms: example@phone.co"
        if "@" not in message[1] and "." not in message[1]:
            return "📲Please provide a valid email address"
        if store_sms(nodeID, message[1]):
            return "📲SMS address set 📪"
        else:
            return "⛔️Failed to set address"
        
    if message.lower().startswith("sms:"):
        message = message.split(" ", 1)
        if any(item['nodeID'] == nodeID for item in sms_db):
            count = 0
            # for all dict items maching nodeID in sms_db send sms
            for item in sms_db:
                if item['nodeID'] == nodeID:
                    smsEmail = item['sms']
                    logger.info("System: Sending SMS for " + str(nodeID) + " to " + smsEmail[:-6])
                    send_email(smsEmail, message[1], nodeID)
                    count += 1
            return f"📲SMS-sent {count} 📤"
        else:
            return "📲No address set, use 📲setsms"
    
    return "Error: ⛔️ not understood. use:setsms example@phone.co"

def handle_email(nodeID, message):
    global email_db
    # send email to email in db. if none ask for one
    if message.lower().startswith("setemail:"):
        message = message.split(" ", 1)
        if "@" not in message[1] and "." not in message[1]:
            return "📧Please provide a valid email address"
        if store_email(nodeID, message[1]):
            return "📧Email address set 📪"

        return "Error: ⛔️ not understood. use:setmail bob@example.com"
        
    if message.lower().startswith("email:"):
        message = message.split(" ", 1)

        # if user sent: email bob@none.net # Hello Bob
        if "@" in message[1] and "#" in message[1]:
            toEmail = message[0].strip()
            message = message[1].split("#", 1)
            logger.info("System: Sending email for " + nodeID)
            send_email(toEmail, message[1], nodeID)
            return "📧Email-sent 📤"

        if nodeID in email_db:
            logger.info("System: Sending email for " + nodeID)
            send_email(email_db[nodeID], message[1], nodeID)
            return "📧Email-sent 📤"

        return "Error: ⛔️ not understood. use:email bob@example.com # Hello Bob"
    

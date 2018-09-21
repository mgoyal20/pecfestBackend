import smtplib
from  email.mime.text import MIMEText
import email

def send_mail(to,msg):
    email_msg = MIMEText(msg)
    email_msg['To'] = to
    email_msg['From'] = 'onlineteam.pecfest@gmail.com'
    email_msg['Subject'] = 'PECFEST 2017'

    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login('onlineteam.pecfest@gmail.com','onlinepublicity')
    server.set_debuglevel(True)
    success = True
    try:
        server.sendmail('onlineteam.pecfest@gmail.com',[to],email_msg.as_string())
    except:
        success = False
    finally:
        server.quit()

    if success:
        return True
    return False

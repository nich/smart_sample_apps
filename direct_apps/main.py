'''SMART Direct Apps backend server'''
# Developed by: Nikolai Schwertner
#
# Revision history:
#     2011-10-04 Initial release

# Import some general modules
import json
import string
import web
import urllib
import rdflib
import os
import sys

# Add the current directory to the system path so that python can mod_py could
# load the local modules
abspath = os.path.dirname(__file__)
sys.path.append(abspath)

# Import the local smart client modules and components
from smart_client import oauth
from smart_client.smart import SmartClient
from smart_client.rdf_utils import anonymize_smart_rdf

# Import the local markdown module function
from lib.markdown2 import markdown

# Import additional components
from StringIO import StringIO
from sendmail import send_message
from pdf_writer import generate_pdf

# Import the application settings
from settings import APP_PATH, SMTP_HOST, SMTP_USER, SMTP_PASS
from settings import SMTP_HOST_ALT, SMTP_USER_ALT, SMTP_PASS_ALT
from settings import PROXY_OAUTH, PROXY_PARAMS, SMART_DIRECT_PREFIX

# Default configuration settings for the SMART client
SMART_SERVER_OAUTH = {
#    'consumer_key': 
    'consumer_secret': 'smartapp-secret'
}

SMART_SERVER_PARAMS = {
#    'api_base': 
}

# URL mappings for web.py
urls = ('/smartapp/index.html', 'index_apps',
        '/smartapp/index-msg.html', 'index_msg',
        '/smartapp/index-apps.html', 'index_apps',
        '/smartapp/getapps', 'get_apps',
        '/smartapp/getmeds', 'get_meds',
        '/smartapp/getproblems', 'get_problems',
        '/smartapp/getrecipients', 'get_recipients',
        '/smartapp/getdemographics', 'get_demographics',
        '/smartapp/getuser', 'get_user',
        '/smartapp/sendmail-msg', 'send_msg_message',
        '/smartapp/sendmail-apps', 'send_apps_message')

class index_msg:
    '''Handler for the SMART Direct Messages app page'''
    
    def GET(self):
        f = open(APP_PATH + '/templates/index-msg.html', 'r')
        html = f.read()
        f.close()
        return html
        
class index_apps:
    '''Handler for the SMART Direct Applications app page'''
    
    def GET(self):
        f = open(APP_PATH + '/templates/index-apps.html', 'r')
        html = f.read()
        f.close()
        return html
        
class get_recipients:
    '''Recipients REST service handler
    
    Returns the list of direct recipients in JSON format
    '''
    
    def GET(self):
        # First, try setting up a dummy SMART client to test the credentials
        # for securty reasons (will raise excepton if the credentails are bad)
        get_smart_client()
    
        # Now process the request
        f = open(APP_PATH + '/data/addresses.json', 'r')
        res = f.read()
        f.close()
        return res
        
class get_apps:
    '''Apps REST service handler
    
    Returns the manifests of the available apps in JSON format
    '''
    
    def GET(self):
        # First, try setting up a dummy SMART client to test the credentials
        # for securty reasons (will raise excepton if the credentails are bad)
        get_smart_client()
    
        # Now process the request
    
        #smart_client = SmartClient(PROXY_OAUTH['consumer_key'], PROXY_PARAMS, PROXY_OAUTH, None)
        #apps_json = smart_client.get("/apps/manifests/")
        #apps = json.loads(apps_json)
        #apps = sorted(apps, key=lambda app: app['name'])
        #return json.dumps(apps)
        
        f = open(APP_PATH + '/data/apps.json', 'r')
        res = f.read()
        f.close()
        return res
        
class get_meds:
    '''Medications REST service handler
    
    Provides select medications data from the SMART server in JSON format
    '''
    
    def GET(self):
    
        #Initialize the SMART client
        smart_client = get_smart_client()
        
        # Query the SMART server for medications data
        meds = smart_client.records_X_medications_GET()
        
        q = """
            PREFIX dc:<http://purl.org/dc/elements/1.1/>
            PREFIX dcterms:<http://purl.org/dc/terms/>
            PREFIX sp:<http://smartplatforms.org/terms#>
            PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
               SELECT  ?name
               WHERE {
                      ?med rdf:type sp:Medication .
                      ?med sp:drugName ?medc.
                      ?medc dcterms:title ?name.
               }
            """
            
        pills = meds.query(q)
        
        # Construct and return the JSON data dump
        out = []

        for pill in pills:
            out.append ({'drug': pill})

        return json.dumps(out)
        
class get_problems:
    '''Problems REST service handler
    
    Provides select problems data from the SMART server in JSON format
    '''
    
    def GET(self):
    
        #Initialize the SMART client
        smart_client = get_smart_client()
        
        # Query the SMART server for medications data
        problems = smart_client.records_X_problems_GET()
        
        q = """
            PREFIX dc:<http://purl.org/dc/elements/1.1/>
            PREFIX dcterms:<http://purl.org/dc/terms/>
            PREFIX sp:<http://smartplatforms.org/terms#>
            PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
               SELECT  ?name ?date
               WHERE {
                      ?p rdf:type sp:Problem .
                      ?p sp:startDate ?date.
                      ?p sp:problemName ?pn.
                      ?pn dcterms:title ?name.
               }
            """
            
        problems = problems.query(q)
        
        # Construct and return the JSON data dump
        out = []

        for problem in problems:
            out.append ({'problem': str(problem[0]), 'date': str(problem[1])})
        
        return json.dumps(out)
        
class get_demographics:
    '''Demographics REST service handler
    
    Provides select patient demographics data from the SMART server in JSON format
    '''
    
    def GET(self):
    
        #Initialize the SMART client
        smart_client = get_smart_client()
        
        # Query the SMART server for demographics data
        demographics = smart_client.records_X_demographics_GET()
        
        q = """
            PREFIX foaf:<http://xmlns.com/foaf/0.1/>
            PREFIX v:<http://www.w3.org/2006/vcard/ns#>
            PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT  ?firstname ?lastname ?gender ?birthday
            WHERE {
               ?r v:n ?n .
               ?n rdf:type v:Name .
               ?n v:given-name ?firstname .
               ?n v:family-name ?lastname .
               ?r foaf:gender ?gender .
               ?r v:bday ?birthday .
            }
            """
            
        name = demographics.query(q)
        
        # Make sure there is exactly one set of demographics data
        assert len(name) == 1, "Bad demographics RDF"
        
        # Construct and return the JSON data dump
        n = list(name)[0]
        out = {'firstname': str(n[0]), 'lastname': str(n[1]), 'gender': str(n[2]), 'birthday': str(n[3])}
        return json.dumps(out)

class get_user:
    '''User Data REST service handler
    
    Provides select user data from the SMART server in JSON format
    '''
    
    def GET(self):
    
        #Initialize the SMART client
        smart_client = get_smart_client()
        
        # Query the SMART server for user data
        user = smart_client.users_X_GET()
        
        q = """
            PREFIX foaf:<http://xmlns.com/foaf/0.1/> 
            PREFIX sp:<http://smartplatforms.org/terms#>
            PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT  ?firstname ?lastname ?email
            WHERE {
               ?r foaf:givenName ?firstname .
               ?r foaf:familyName ?lastname .
               ?r foaf:mbox ?email .
            }
            """
            
        name = user.query(q)
        
        # Make sure there is exactly one set of user data
        assert len(name) == 1, "Bad user RDF"
        
        # Construct and return the JSON data dump
        n = list(name)[0]
        out = {'name': str(n[0]) + ' ' + str(n[1]), 'email': str(n[2]).replace("mailto:","")}
        return json.dumps(out)
 
class send_msg_message:
    '''SMART Direct Messages sender REST service handler
    
    Processes send message requests for the SMART Direct Messages app
    '''
    
    def POST(self): 
        # First, try setting up a dummy SMART client to test the credentials
        # for securty reasons (will raise excepton if the credentails are bad)
        get_smart_client()
    
        # Load the message parameters
        me = SMTP_USER + "@" + SMTP_HOST # we always use the primary SMART Direct address
        you = web.input().recipient_email
        subject = web.input().subject
        message = web.input().message
   
        # Create the body of the message (plain-text and HTML version).
        text = message
        html = markdown(text)
        
        # Generate the PDF attachment content
        pdf_buffer = generate_pdf (html)
        
        # Initialize the attachment and general settings for the mailer
        attachments = [{'file_buffer': generate_pdf(html), 'name': "patient.pdf", 'mime': "application/pdf"}]
        settings = {'host': SMTP_HOST, 'user': SMTP_USER, 'password': SMTP_PASS}
        
        # Send the SMART Direct message
        send_message (me, you, subject, text, html, attachments, settings)
        
        # Clean up the string buffer
        pdf_buffer.close()
        
        # Respond with success message
        return json.dumps({'result': 'ok'})
 
class send_apps_message:
    '''SMART Direct Applications sender REST service handler
    
    Processes send message requests for the SMART Direct Applications app
    '''
    
    def POST(self):
        # First, try setting up a dummy SMART client to test the credentials
        # for securty reasons (will raise excepton if the credentails are bad)
        get_smart_client()
        
        # Initialize the SMART client
        smart_client = get_smart_client()

        # Load the message parameters
        sender = web.input().sender_email
        recipient = web.input().recipient_email
        subject = SMART_DIRECT_PREFIX + web.input().subject
        message = web.input().message
        apps = string.split (web.input().apps, ",")
        apis = []
    
        # Generate the end-point direct addresses for the first message hop
        me = SMTP_USER_ALT + "@" + SMTP_HOST_ALT
        you = SMTP_USER + "@" + SMTP_HOST
        
        # Load the app manifests JSON 
        FILE = open(APP_PATH + '/data/apps.json', 'r')
        APPS_JSON = FILE.read()
        FILE.close()
        
        # Parse the apps manifests JSON
        myapps = json.loads(APPS_JSON)
        
        # Initialize the outbound manifest data object
        manifest= {"from": sender,
                   "to": recipient,
                   "apps": []}
        
        # Populate the manifest object with a subset of the manifest data
        # for the selected apps. Also build a list of the APIs needed by the
        # selected aps.
        for a in myapps:
            if (a['id'] in apps):
                myapis = a['apis']
                for i in myapis:
                    if (i not in apis):
                        apis.append(i)
                del(a['apis'])
                del(a['name'])
                del(a['icon'])
                manifest["apps"].append(a)
        
        # Load the manifest in a string buffer (in JSON format)
        manifesttxt = json.dumps(manifest)
        manifestbuffer = StringIO()
        manifestbuffer.write(manifesttxt)
        
        # Build the patient RDF graph
        rdfres = smart_client.records_X_demographics_GET()
        
        if ("problems" in apis):
            rdfres += smart_client.records_X_problems_GET()
            
        if ("medications" in apis):
            rdfres += smart_client.records_X_medications_GET()
            
        if ("vital_signs" in apis):
            rdfres += smart_client.records_X_vital_signs_GET() 
        
        # Anonymize the RDF graph for export
        rdfres = anonymize_smart_rdf (rdfres)
        
        # Serialize the RDF graph in a string buffer
        rdftext = rdfres.serialize()
        rdfbuffer = StringIO()
        rdfbuffer.write(rdftext)
        
        # Initialize the attachments descriptor object
        attachments = [
            {'file_buffer': rdfbuffer, 'name': "patient.xml", 'mime': "text/xml"},
            {'file_buffer': manifestbuffer, 'name': "manifest.json", 'mime': "text/xml"}
        ]
        
        # Initialize the mailer settings
        settings = {'host': SMTP_HOST_ALT, 'user': SMTP_USER_ALT, 'password': SMTP_PASS_ALT}
        
        # Send the SMART Direct message
        send_message (me, you, subject, message, message, attachments, settings)
        
        # Clean up the string buffers
        manifestbuffer.close()
        rdfbuffer.close()
        
        # Respond with success message
        return json.dumps({'result': 'ok'})
        
def get_smart_client():
    '''Initializes and returns a new SMART Client
    
    Expects an OAUTH header as a REST parameter
    '''
    smart_oauth_header = web.input().oauth_header
    smart_oauth_header = urllib.unquote(smart_oauth_header)
    oa_params = oauth.parse_header(smart_oauth_header)
    SMART_SERVER_PARAMS['api_base'] = oa_params['smart_container_api_base']
    SMART_SERVER_OAUTH['consumer_key'] = oa_params['smart_app_id']

    oa_params = oauth.parse_header(smart_oauth_header)
    
    resource_tokens={'oauth_token':       oa_params['smart_oauth_token'],
                     'oauth_token_secret':oa_params['smart_oauth_token_secret']}

    ret = SmartClient(SMART_SERVER_OAUTH['consumer_key'], 
                       SMART_SERVER_PARAMS, 
                       SMART_SERVER_OAUTH, 
                       resource_tokens)
                       
    ret.record_id=oa_params['smart_record_id']
    ret.user_id=oa_params['smart_user_id']
    
    return ret

# Initialize web.py
web.config.debug=False
app = web.application(urls, globals())

#if web.config.get('_session') is None:
#    session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'client': None})
#    session = web.session.Session(app, web.session.ShelfStore(shelve.open(APP_PATH+'session.shelf')), initializer={'client': None, 'cookie_name': ''})
#    web.config._session = session
#else:
#    session = web.config._session

if __name__ == "__main__":
    app.run()
else:
    application = app.wsgifunc()
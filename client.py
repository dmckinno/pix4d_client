import boto
import requests
from boto.s3.connection import OrdinaryCallingFormat
import os
import simplejson as json
import re
import urllib2
from colorama import init
init()

client_id = 'YOUR CLIENT ID'
client_secret = 'YOUR CLIENT SECRET'
password = 'YOUR PW'


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
	
def upload_project(s3_credentials, image_list):
    # Connect to s3 using the temporal credentials an get the bucket where you need to upload the project
    s3conn, bucket = connect_to_s3(s3_credentials)
    n = 1
    # Iterate over all the images to upload them
    for image in image_list:
        upload_image_to_s3(s3_credentials["key"], bucket, image, n)
        n += 1
    return n

def connect_to_s3(s3_credentials):
    # Connect to the bucket
    s3conn = boto.connect_s3(aws_access_key_id=s3_credentials["access_key"], aws_secret_access_key=s3_credentials["secret_key"], security_token=s3_credentials['session_token'], calling_format=OrdinaryCallingFormat())
    # Get the bucket
    bucket = s3conn.get_bucket(s3_credentials["bucket"], validate=False, headers={'x-amz-security-token': s3_credentials['session_token']})
    return s3conn, bucket

def upload_image_to_s3(key_root, bucket, image, n):
    # Build the key name where the file is going to be uploaded
    # e.g. username@example.com/project_test/img001.jpg
    image_name = image.split("/")[-1]
    key_name =  key_root + "/" + image_name
    # Create the bucket key
    key = bucket.new_key(key_name)
    # Upload the content
    try:
        response = key.set_contents_from_filename(image)
        if response: # Check if it succeeded
            print "Image" + str(n) + "/"+str(len(image_list))+" uploaded"         
            # print response
            # Call to register the input in Cloud Service
            # ... POST projects/{id}/register_input/
            # end
    except Exception as e:
            print "[bad] -----------"
            print e
            print key_root
            print key

def flat(l):
    def _flat(l, r):    
        if type(l) is not list:
            r.append(l)
        else:
            for i in l:
                r = r + flat(i)
        return r
    return _flat(l, [])

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def int_conv(string):
    try:
        i = int(string)
        return i
    except ValueError:
        return 0
              
if __name__ == '__main__':

    mode = raw_input(bcolors.OKBLUE + "Do you want to PROCESS a job or CHECK on a job you have already processed? " + bcolors.ENDC)

    if mode.upper() == 'PROCESS':
    
        token_url = 'https://mapper.pix4d.com/oauth2/token/'
    
        pix4d_token_req = requests.post(token_url, data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
            }, headers={
            'username': 'mckinnon@3drobotics.com',
            'password': password
            })
        
        pix4d_token = pix4d_token_req.json()
    
        pix4d_api_credentials = {
            'Authorization': pix4d_token['token_type'] + ' '+ pix4d_token['access_token'],
            'username': 'mckinnon@3drobotics.com'
        }
    
        create_url = 'https://mapper.pix4d.com/api/v2/projects/'
    
        mission_name = raw_input(bcolors.OKBLUE + "What would you like to call your new mission? " + bcolors.ENDC)
        
        image_folder = raw_input(bcolors.OKBLUE + "Enter the directory of your folder containing the images you would like to process. " + bcolors.ENDC)

        images = []
        for root, dirs, files in os.walk(image_folder):
            for file in files:
                if file.lower().endswith('.jpg') or file.endswith('.JPG'):
                    images.append(file)
        
        image_list = []
        
        for x in images:
            image_list.append(image_folder + x)
        
        number_images = len(image_list)
    
        create_mission_req = requests.post(create_url, headers=pix4d_api_credentials, data={
            'name' : mission_name,
            'image_count' : number_images,
            })
    
        create_mission = create_mission_req.json()

        print bcolors.OKBLUE + "Mission created. Your mission ID is " + str(create_mission['id']) +". Write down this number to retrieve results." + bcolors.ENDC

        s3_url = 'https://mapper.pix4d.com/api/v2/projects/'+str(create_mission['id'])+'/s3_credentials/'
    
        req = requests.get(s3_url, headers=pix4d_api_credentials)

        print bcolors.OKBLUE + "Project uploading. This may take a moment." + bcolors.ENDC
    
        upload_project(req.json(), image_list)

        print bcolors.OKBLUE + "Images uploaded. Posting images to Pix4D project." + bcolors.ENDC
    
        post_pics_url = 'https://mapper.pix4d.com/api/v2/projects/'+str(create_mission['id'])+'/register_input/'
    
        image_list_simple = [0] * len(image_list)
        
        for x in range(0,len(image_list)):
            image_list_simple[x] = image_list[x].split('/')[1]
    
        for image_simple in image_list_simple:
            requests.post(post_pics_url, headers=pix4d_api_credentials, data={'rel_path' : image_simple, 'type' : 'image'})

        process_url = 'https://mapper.pix4d.com/api/v2/projects/'+str(create_mission['id'])+'/process/'
    
        status = requests.get(process_url, headers=pix4d_api_credentials)
    
        if status.json()['detail'] == "Project submitted for processing":
            print bcolors.OKBLUE + "Your mission has been successfully submitted for processing. Rerun this program with mission ID " + str(create_mission['id']) + " to retrieve results." + bcolors.ENDC
        else: 
            print bcolors.FAIL + "Your mission failed. Try again :-)" + bcolors.ENDC
    
    elif mode.upper() == 'CHECK':
        
        mission_ID = raw_input(bcolors.OKBLUE + "What is you mission ID? " + bcolors.ENDC)
        
        token_url = 'https://mapper.pix4d.com/oauth2/token/'
    
        pix4d_token_req = requests.post(token_url, data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
            }, headers={
            'username': 'mckinnon@3drobotics.com',
            'password': password
            })
        
        pix4d_token = pix4d_token_req.json()
    
        pix4d_api_credentials = {
            'Authorization': pix4d_token['token_type'] + ' '+ pix4d_token['access_token'],
            'username': 'mckinnon@3drobotics.com'
        }

        job_status_url = 'https://mapper.pix4d.com/api/v2/projects/'+str(mission_ID)+'/status/'
        
        job_status = requests.get(job_status_url, headers=pix4d_api_credentials)
        
        if job_status.json()['description'] == 'Project processed':
            job_download_url = 'https://mapper.pix4d.com/api/v2/projects/'+str(mission_ID)+'/output/'
            results = requests.get(job_download_url, headers=pix4d_api_credentials)
            print bcolors.OKBLUE + "Your results can also be viewed graphically in the Pix4D web app at https://mapper.pix4d.com/. Just login with your credentials." + bcolors.ENDC
            print bcolors.OKBLUE + "Otherwise, grab one of the URLs below. Note that full resolution processing is currently in the works." + bcolors.ENDC
            result_string = list(flat(json.dumps(results.json(), sort_keys=True)))[0]
            old_list = result_string.split(": ")
            regex = re.compile('^\"http')
            new_list = [s for s in old_list if regex.match(s)]    
            
            counter = 0
            links = []
            for i in new_list:
                # Extract the file name
                name_first_part = find_between(i, "/", "?")
                name = name_first_part.split("/")[-1]
                print str(counter+1) + ".- " + name
                links.append([name, find_between(i, "\"", "\"")]) #append file name and link
                counter += 1
            
            download = raw_input(bcolors.OKBLUE + "Select a file to download: " + bcolors.ENDC)
            download = int_conv(download)
            
            if download > 0:
                if download not in range (1, counter+1):
                    print bcolors.FAIL + "That was not an option. Try again." + bcolors.ENDC
                else:
                    # Code from PabloG http://stackoverflow.com/questions/22676/how-do-i-download-a-file-over-http-using-python
                    file_name = links[download-1][0]
                    url = links[download-1][1]

                    # Open the url
                    u = urllib2.urlopen(url)
                    f = open(file_name, 'wb')
                    meta = u.info()
                    file_size = int(meta.getheaders("Content-Length")[0])
                    print "Downloading: %s Bytes: %s" % (file_name, file_size)

                    file_size_dl = 0
                    block_sz = 8192
                    while True:
                        buffer = u.read(block_sz)
                        if not buffer:
                            break

                        file_size_dl += len(buffer)
                        f.write(buffer)
                        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                        status = status + chr(8)*(len(status)+1)
                        print status,
                    
                    f.close()

            else:
                print bcolors.FAIL + "That was not an option. Try again." + bcolors.ENDC
                            
        elif job_status.json()['description'] == 'Waiting for processing':
            print bcolors.OKGREEN + "Your job is processing. We have no idea how long this will take so hang tight." + bcolors.ENDC
        else:
            print bcolors.FAIL + "Your job is FUBAR. Sorry. :-(" + bcolors.ENDC

    else:
        print bcolors.FAIL + "That was not an option. Try again." + bcolors.ENDC
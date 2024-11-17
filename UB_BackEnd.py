from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime

import sqlite3, uuid, hashlib, hmac, re, imageio.v3 as iio, face_recognition, os

ub_app = FastAPI()

origins = [ "http://localhost", "http://localhost:3000" ]

ub_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=[ "*" ],
    allow_headers=[ "*" ],
)

"""The below root route is just for testing purposes, so commented out.
@ub_app.get( "/" )
def testing():
    return { "msg": "great!" }
"""

@ub_app.post( "/add_customer" )
async def add_cust( payload: Request ):
    parameters = await payload.json()
    parameters[ "customer_id" ] = str( uuid.uuid4().int )[ 0:12 ]

    print( ">>> Params: ", parameters )

    status = "Customer ID for " + parameters[ "fname" ] + " " + parameters[ "mname" ] + " " + parameters[ "lname" ] + " is: " + parameters[ "customer_id" ] 
    salt = bytes( "2646753189180891", "utf-8" )
    password_hash = hashlib.pbkdf2_hmac( "sha256", parameters[ "password" ].encode(), salt, 100000 )

    if (not parameters[ "fname" ] or not parameters[ "lname" ]\
            or not parameters[ "email"] or not parameters[ "mobile" ]\
            or not parameters[ "address" ] or not parameters[ "password" ]\
            or not parameters[ "dob" ]):
            status = "Must fill all fields except Middle Name"
            return ( status )
    elif(parameters[ "dob" ] >= str(date.today())):
        status = 'Wrong Format for dob (DOB must be before today)'
        return ( status )
    elif(not re.search("^.+@.+\..+$", parameters[ "email" ] )):
        status = "Wrong Format for email (must be in the format id@website.domain)"
        return ( status )
    elif(re.search("\D", parameters[ "mobile" ]) or len(parameters[ "mobile" ])!= 10\
        or parameters[ "mobile" ][0]=='0'):
        status = "Wrong Format for mobile number (must have ten digits and not start with zero)"
        return ( status )
    elif(len(parameters[ "address" ]) < 10 or not re.search("[0-9]{6}$", parameters[ "address" ])):
        status = "Wrong Format for address (Address should have at least ten characters with city name and zip code)"
        return ( status )
    else:
        try: 
            db_conn = sqlite3.connect( "UB.db" )
            cursor = db_conn.cursor()

            dml = "INSERT INTO customer VALUES ( '"
            dml += parameters[ "customer_id" ] + "', '"
            dml += parameters[ "fname" ] + "', '"
            dml += parameters[ "mname" ] + "', '"
            dml += parameters[ "lname" ] + "', '"
            dml += parameters[ "dob" ] + "', '"
            dml += parameters[ "email" ] + "', '"
            dml += parameters[ "mobile" ]+ "', '"
            dml += parameters[ "address" ] + "', "
            dml += "?" + ", "
            dml += "?" + ", "
            dml += "'', "
            dml += "'N' );"

            sql_param = ( password_hash, 1001, )
            cursor.execute( dml, sql_param )
            db_conn.commit()
            db_conn.close()

        except sqlite3.Error as e:
            err_msg = str( e )
            if ( "UNIQUE constraint" in err_msg ):
                status = "ERROR: Customer already exists with name '" + parameters[ "fname" ] + " " + parameters[ "mname" ] + " " + parameters[ "lname" ] + "'"
            else:
                status = err_msg
            db_conn.close()

    print( ">>> dml: ", dml )
    print( ">>> Status: ", status )

    return( status )

@ub_app.post( "/view_trans" )
async def view_cust( payload: Request ):
    parameters = await payload.json()
    ctr_id = parameters[ "ctr_id" ]
    db_conn = sqlite3.connect( "UB.db" )

    cursor = db_conn.cursor()

    dml = "select * from account where cust_id = " + str(ctr_id)

    res = cursor.execute( dml )

    res = res.fetchall()

    print( ">>> Fetchall transactions", res )

    db_conn.close()

    return ( str( res ) )

@ub_app.post( "/deactivate_customer" )
async def deactivate_cust( payload: Request ):
    parameters = await payload.json()
    if parameters["type"] != "mgr":
        return "Need higher level access to deactivate customer. Contact admin."  
    db_conn = sqlite3.connect("UB.db")
    db_conn.row_factory = sqlite3.Row
    cursor = db_conn.cursor()
    #first check if customer exists and deleted flag is set to N
    dml = f'SELECT * FROM customer where cust_id = {parameters["id"]};'
    customer_info = cursor.execute(dml)
    row = customer_info.fetchone()
    if row:
        if row['deleted'] == 'N':
            dml = f'UPDATE customer SET deleted="Y" WHERE cust_id = {parameters["id"]};'
            cursor.execute(dml)
            status = f"Successfully deactivated customer {parameters['id']}"
        else:
            status = f"Customer with ID: {parameters['id']} already deactivated"
        db_conn.commit()
        db_conn.close()
        return status
    else:
        return f"No Customer with ID: {parameters['id']}"

@ub_app.post( "/view_customer" )
async def view_cust( payload: Request ):
    parameters = await payload.json()
    if parameters["type"] != "mgr":
        return "Need higher level access to view customer details. Contact admin."  
    
    db_conn = sqlite3.connect("UB.db")
    db_conn.row_factory = sqlite3.Row 
    cursor = db_conn.cursor()
    #first check if customer exists
    dml = f'SELECT * FROM customer where cust_id = {parameters["id"]};'
    customer_info = cursor.execute(dml)
    row = customer_info.fetchone()
    #column names to display -- fname mname lname dob email mobile address balance
    if row:
        status = {
            'data': {
                'fname':row['fname'],
                'mname':row['mname'],
                'lname':row['lname'],
                'dob':row['dob'],
                'email':row['email'],
                'mobile':row['mobile'],
                'address':row['address'],
                'balance':row['balance'],
            },
            'response_code':'Success',
        }
    else:
        status = {
            'data': None,
            'response_code':f"Customer with ID: {parameters['id']} does not exist"
        }
    db_conn.commit()
    db_conn.close()
    return status

@ub_app.get("/view_customers" )
async def view_customers():

    print( ">>> Within View_Customers" )

    db_conn = sqlite3.connect( "UB.db" )

    cursor = db_conn.cursor()

    dml = "select cust_id, fname, mname, lname, dob, email, mobile, address, deleted from customer"

    res = cursor.execute( dml )

    res = res.fetchall()

    print( ">>> Fetchall customers", res )

    db_conn.close()

    return ( str( res ) )

def checks(parameters):
    if(parameters[ "dob" ] >= str(date.today())):
        status = 'Wrong Format for dob (DOB must be before today)'
        return ( status, 0 )
    elif(not re.search("^.+@.+\..+$", parameters[ "email" ] )):
        status = "Wrong Format for email (must be in the format id@website.domain)"
        return ( status, 0 )
    elif(re.search("\D", parameters[ "mobile" ]) or len(parameters[ "mobile" ])!= 10\
        or parameters[ "mobile" ][0]=='0'):
        status = "Wrong Format for mobile number (must have ten digits and not start with zero)"
        return ( status, 0 )
    elif(len(parameters[ "address" ]) < 10 or not re.search("[0-9]{6}$", parameters[ "address" ])):
        status = "Wrong Format for address (Address should have at least ten characters with city name and zip code)"
        return ( status, 0 )
    return "ok",1

@ub_app.post( "/modify_customer" )
async def modify_cust( payload: Request ):
    parameters = await payload.json()
    if parameters["type"] != "mgr":
        return "Need higher level access to deactivate customer. Contact admin."  
    keys = [['fname','updated_fname'], ['mname','updated_mname'],['lname','updated_lname'],['dob','updated_dob'],['email','updated_email'],['mobile','updated_mobile'],['address','updated_address'],['deleted','updated_account']]
    if parameters['updated_account'] == 'Deactivated':
        parameters['updated_account'] = 'Y'
    else:
        parameters['updated_account'] = 'N'
    new_data = {}
    for key in keys:
        new_data[key[0]] = parameters[key[1]]
    print(new_data)
    status, code = checks(new_data)
    if not code:
        return status
    db_conn = sqlite3.connect("UB.db")
    db_conn.row_factory = sqlite3.Row
    cursor = db_conn.cursor()
    #first check if customer exists
    dml = f'SELECT * FROM customer where cust_id = {parameters["id"]};'
    customer_info = cursor.execute(dml)
    row = customer_info.fetchone()
    if row:
        for key in keys:
            if parameters[key[1]]:
                dml = f'UPDATE customer SET {key[0]}="{parameters[key[1]]}" WHERE cust_id = {parameters["id"]};'
                cursor.execute(dml)
        status = f"Successfully changed info for customer {parameters['id']}"
    else:
        status = f"Customer with ID: {parameters['id']} hasn't made account in our bank before."
    db_conn.commit()
    db_conn.close()
    return status

@ub_app.post( "/validate_password" )
async def validate_password( payload: Request ):
    parameters = await payload.json()    
    print( ">>> Params: ", parameters )

    status = "Error logging in with the entered credentials!"

    salt = bytes( "2646753189180891", "utf-8" )

    try:
        db_conn = sqlite3.connect( "UB.db" )
        cursor = db_conn.cursor()
        if ( parameters[ "type" ] == "mgr" ):
            dml = "select password_hash from manager where mgr_id = '" + parameters[ "id" ] + "';"
        else:
            cmd = 'select deleted from customer where cust_id = "' + parameters[ "id" ] + '";'
            flag = cursor.execute(cmd)
            flag = flag.fetchone()[0]
            if(str(flag) != 'N'):
                status = "Customer account is deactivated! Contact the Manager."
                return( status )
            dml = "select password_hash from customer where cust_id = '" + parameters[ "id" ] + "';"

        ret_values = cursor.execute( dml )
        row = ret_values.fetchone()

        dml = "select fname from customer where cust_id = '" + parameters[ "id" ] + "';"
        ret = cursor.execute( dml )
        name = ret.fetchone()[0]

        if row:
            hash = row[ 0 ]
        else:
            return ( status )

    except sqlite3.Error as e:
        print( ">>> There was an error fetching password hash: ", str(e) )
        return( status )
    
    print( ">>> hash:", hash, ":: id:", parameters[ "id" ], ":: salt", salt, ":: pwd: ", parameters[ "pwd" ].encode() )
    check = hmac.compare_digest( hash, hashlib.pbkdf2_hmac( "sha256", parameters[ "pwd" ].encode(), salt, 100000 ) )
    print( ">>> check:", check )

    if check:
        status = name + " Successful login"

    return ( status )

def Capture_Frames():
    print( ">>> Capturing frames from webcam..." )
    for frame_counter, frame in enumerate( iio.imiter( "<video0>" ) ):
        iio.imwrite( f"Frame_{ frame_counter }.jpg", frame )
        print( ">>> Frame", frame_counter, "stored in file" )
        if frame_counter > 9:
            break

@ub_app.post( "/manager_login" )
async def manager_login( payload: Request ):
    parameters = await payload.json()
    mgr_id = parameters[ "mgr_id" ]

    print( ">>> Capturing Frames..." )
    Capture_Frames()

    # Compare stored image passed as command line argument with captured frames
    print( ">>> Reading stored image" )

    try:
        con = sqlite3.connect( "UB.db" )
        cur = con.cursor()
        dml = "select fname, face from manager where mgr_id='" + mgr_id + "'"
        res = cur.execute( dml )
        ( stored_face_name, stored_face_blob ) = res.fetchone()
        
        with open( "Retrieved.jpg", "wb" ) as stored_face:
            stored_face.write( stored_face_blob )

    except sqlite3.Error as e:
        err_msg = ">>> ERROR: while trying to retrieve & store face for Manager ID" + mgr_id + " - " + e
        print( err_msg )
        return( err_msg )


    stored_face_image = face_recognition.load_image_file( "Retrieved.jpg" )
    stored_face_encoding = face_recognition.face_encodings( stored_face_image )[0]

    res = [False]
    success_frame = -1
    for counter in range( 0, 11 ):
        print( ">>> Reading frame number:", counter )
        captured_frame = "Frame_" + str( counter ) + ".jpg"
        captured_frame_image = face_recognition.load_image_file( captured_frame )
        try:
            captured_frame_encoding = face_recognition.face_encodings( captured_frame_image )[ 0 ]
        except: # No face found in captured frame, so continue to next frame
            print( ">>> Either no face or multiple faces found in frame", counter )
            continue

        print( ">>> Comparing frame number", counter, "to stored image" )
        res = face_recognition.compare_faces( [ stored_face_encoding ], captured_frame_encoding )
        
        if ( res == [True] ):
            success_frame = counter
            break
    
    for i in range(11):
        try:
            captured_frame = "Frame_" + str( i ) + ".jpg"
            os.remove(captured_frame)
            print(">>> Removed: " + captured_frame)
        except OSError as e:
            print(">>> Error deleting frame image file: " + str(e))
    try:
        os.remove("Retrieved.jpg")
        print(">>> Removed: Retrieved.jpg")
    except OSError as e:
        print(">>> Error deleting retrieved image file: " + str(e))

    if ( res == [False] ):
        print( ">>> NO MATCH FOUND!" )
        return( "Login error - no matching face found" )
    else:
        print( ">>> SUCCESS: MATCH FOUND IN FRAME", success_frame, "!" )
        return( stored_face_name + " :: Successful login!" )

@ub_app.post( "/balance_enquiry" )
async def balance_enquiry( payload: Request ):
    parameters = await payload.json()
    ctr_id = parameters[ "ctr_id" ]
    status = "Error fetching Balance"
    try:
        db_conn = sqlite3.connect( "UB.db" )
        cursor = db_conn.cursor()
        cmd = "select balance from customer where cust_id = '"+ctr_id+"'"
        res = cursor.execute( cmd )
        bal = res.fetchone()
        status = "Your current balance is Rs."+str(bal[0])
        return( status )

    except sqlite3.Error as e:
        print( ">>> There was an error retrieving balance: ", str(e) )
        return( status )

@ub_app.post( "/balance_change" )
async def balance_enquiry( payload: Request ):
    parameters = await payload.json()
    ctr_id = parameters[ "ctr_id" ]
    bal = parameters[ "balance" ]
    trans_type = parameters[ "trans_type" ]
    trans_amount = parameters[ "trans_amount" ]
    
    status = "Error fetching Balance"
    try:
        db_conn = sqlite3.connect( "UB.db" )
        cursor = db_conn.cursor()
        cmd = "update customer set balance = "+str(bal)+" where cust_id = '"+ctr_id+"'"
        if trans_type == 'transfer-receive':
            cmd1 = "select balance from customer where cust_id = '"+ctr_id+"'"
            print( ">>> Cust ID", ctr_id )
            res = cursor.execute( cmd1 )
            bal_original = res.fetchone()
            if bal_original:
                print( ">>> Bal original", bal_original )
                bal_original = bal_original[0]
                bal += int(bal_original)
                print( ">>> Receive balance:", bal ) 
                cmd  = "update customer set balance = "+str(bal)+" where cust_id = '"+ctr_id+"'"
            else:
                return ("Error: No such customer ID")
        cursor.execute( cmd )

        act_id = str( uuid.uuid4().int )[ 0:12 ]
        t_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        print(">>> Update Balance", act_id, ctr_id, t_date)

        cmd = f"INSERT INTO account VALUES ('{ctr_id}-001', '{ctr_id}', '{bal}', '{act_id}', '{t_date}', '{trans_type}', '{trans_amount}');"
        cursor.execute( cmd )
        
        db_conn.commit()
        db_conn.close()

        status = str(bal)
        return( status )

    except sqlite3.Error as e:
        print( ">>> There was an error updating balance: ", str(e) )
        return( status )

@ub_app.post( "/check_customer_id" )
async def check_customer_id( payload: Request ):
    parameters = await payload.json()
    cust_id = parameters[ "cust_id" ]
    try:
        conn = sqlite3.connect( "UB.db" )
        cur = conn.cursor()
        dml = "select * from customer where cust_id = '" + cust_id + "'"
        res = cur.execute( dml )
        res = res.fetchone()
        if res:
            return( "Success :: Customer ID found" )
        else:
            return( "Error :: Customer ID NOT found" )
    
    except sqlite3.Error as e:
        print( ">>> There was an error checking customer id", cust_id, " :: Error is -", e )
        return( "Error while checking customer id", e )
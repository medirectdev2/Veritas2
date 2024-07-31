import calendar as cal
import requests
import re
import os
import logging
import pytz
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
from flask_mail import Mail, Message
from flask import Flask, request, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, bindparam, exc
from datetime import datetime, timedelta  # Step 1: Import timedelta
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Your registered application's details
client_id = '267f4fe7-d947-447a-9a73-a87aed2b7d46'
client_secret = 's5x8Q~pL3DmmKy8mApruGthjedulmhvlo.YoAaqt'
tenant_id = '60dc5bcb-2587-4331-b98d-aa4bdb292cad'
MAIL_USERNAME = 'hsabookings@medirect.com.au'

# Configure your SQL Server connection string.\.venv\Scripts\Activate
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mssql+pyodbc://medirect:x52MZxzCfLJ4psQlQs92'
    '@sql1114.vinciportal.com.au:443/medirect?driver=ODBC+Driver+17+for+SQL+Server'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Simple incremental reference ID generator (for example purposes only)
ref_id_counter = 1

# A helper function to map month numbers to names
def month_number_to_name(month_num):
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return month_names[month_num - 1] if 1 <= month_num <= 12 else None

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    # Define your SQL query
    sql_query = text("""
        SELECT DISTINCT 
            u.FirstName + ' ' + u.LastName AS FullName,
            u.Email,
			u.Position,
            u.Id AS DoctorID
        FROM medirect.dbo.MEDirectBookingCalendar c
        INNER JOIN medirect.dbo.MEDirectBookingSlot s ON c.Id = s.CalendarId
        INNER JOIN medirect.dbo.MEDirectUserAccount u ON c.UserId = u.Id
        INNER JOIN medirect.dbo.MEDirectBranch b ON c.BranchId = b.Id
        LEFT JOIN medirect.dbo.MEDirectCaseService cs ON s.CaseId = cs.Id
        LEFT JOIN medirect.dbo.MEDirectBranch mb ON mb.Id = c.BranchId
		WHERE u.Id IN (8562, 8567, 8566, 8565, 8560,8561,8535,8533)
    """)
    
    try:
        # Execute the query using db.session.execute
        result = db.session.execute(sql_query).fetchall()
        # Convert to a list of dictionaries
        doctors = [{'id': row.DoctorID, 'name': row.FullName} for row in result]  # Check the attribute names
        # Return JSON response
        return jsonify(doctors)
    except Exception as e:
        # Log the exception
        app.logger.error(f"An error occurred when fetching doctors: {e}")
        # Return a JSON error message
        return jsonify({'error': 'Unable to fetch doctors'}), 500


@app.route('/api/slots', methods=['GET'])
def get_slots():
    start_param = request.args.get('start')
    end_param = request.args.get('end')
    doctor_ids = request.args.getlist('doctor_id')  # This could be a list of IDs or ['all']

    # Parse the dates from the request
    utc_zone = pytz.utc
    aus_zone = pytz.timezone('Australia/Sydney')  # Define Canberra/Sydney timezone

    if not start_param or not end_param:
        return jsonify({'error': 'Start and end parameters are required'}), 400
    
    try:
        # Adjust for timezone after parsing the dates
        start_date = utc_zone.localize(datetime.strptime(start_param, '%Y-%m-%dT%H:%M:%S.%fZ')).astimezone(aus_zone)  # Step 2: Adjust for start_date
        end_date = utc_zone.localize(datetime.strptime(end_param, '%Y-%m-%dT%H:%M:%S.%fZ')).astimezone(aus_zone)  # Step 2: Adjust for end_date

    except ValueError as e:
        return jsonify({'error': 'Invalid date format'}), 400

    sql_query = """
        SELECT DISTINCT
            u.FirstName + ' ' + u.LastName as FullName,
            u.Email,
            s.CaseId,
            b.State,
            CONCAT(b.Address1, ', ', b.City, ' ', b.Postcode) as Position,
            b.City,
            b.Postcode,
            s.StartDateTime,
            s.EndDateTime,
            c.BranchId,
            cs.ServiceName,
            u.id as DoctorID,
            mb.Name as BranchName,
            CASE
                WHEN s.IsBooked = 0 THEN 'Not Booked'
                ELSE 'Inactive'
            END as AppointmentStatus
        FROM medirect.dbo.MEDirectBookingCalendar c
        INNER JOIN medirect.dbo.MEDirectBookingSlot s ON c.Id = s.CalendarId
        INNER JOIN medirect.dbo.MEDirectUserAccount u ON c.UserId = u.Id
        INNER JOIN medirect.dbo.MEDirectBranch b ON c.BranchId = b.Id
        LEFT JOIN medirect.dbo.MEDirectCaseService cs On s.CaseId = cs.Id
        LEFT JOIN medirect.dbo.MEDirectBranch mb On mb.id = c.BranchId
        WHERE u.Id IN (8562, 8567, 8566, 8565, 8560,8561,8535,8533)
        AND s.StartDateTime >= :start AND s.EndDateTime <= :end
    """

    # Set up parameters for the query
    params = {'start': start_date, 'end': end_date}

    # Check if 'all' is in doctor_ids, which means no doctor_id filter should be applied
    if 'all' not in doctor_ids:
        # Ensure all doctor_ids are integers
        doctor_ids_int = [int(id_) for id_ in doctor_ids if id_.isdigit()]
        # Include the doctor_ids in the SQL query and params if provided
        if doctor_ids_int:
            placeholders = ', '.join([':doctor_id{}'.format(i) for i in range(len(doctor_ids_int))])
            sql_query += f" AND u.Id IN ({placeholders})"
            params.update({f'doctor_id{i}': doctor_id for i, doctor_id in enumerate(doctor_ids_int)})

    sql_text_obj = text(sql_query)

    try:
        result = db.session.execute(sql_text_obj, params).fetchall()
        slots = [
            {
                'doctor_id': row.DoctorID,
                'doctor_name': row.FullName,
                'branch_name': row.BranchName,
                'start': row.StartDateTime.isoformat(),
                'end': row.EndDateTime.isoformat(),
                'status': row.AppointmentStatus,
            }
            for row in result
        ]
        return jsonify(slots)
    except Exception as e:
        app.logger.error(f"Error fetching slots: {e}")
        return jsonify({'error': 'Error fetching slots.'}), 500
    
@app.route('/api/available-months', methods=['GET'])
def get_available_months():
    try:
        doctor_ids = request.args.getlist('doctor_id')
        app.logger.info(f"Received doctor_ids: {doctor_ids}")

        # Split by comma if doctor_ids is a single string with comma-separated values
        if doctor_ids and ',' in doctor_ids[0]:
            doctor_ids = doctor_ids[0].split(',')
            app.logger.info(f"Split doctor_ids: {doctor_ids}")

        if not doctor_ids or 'all' in doctor_ids:
            doctor_ids_clause = ""
            params = {}
        else:
            doctor_ids_int = []
            for id_ in doctor_ids:
                try:
                    doctor_ids_int.append(int(id_))
                except ValueError:
                    app.logger.error(f'Invalid doctor ID: {id_}')
                    return jsonify({'error': f'Invalid doctor ID: {id_}'}), 400

            placeholders = ', '.join(f":doctor_id_{i}" for i in range(len(doctor_ids_int)))
            doctor_ids_clause = f"AND u.Id IN ({placeholders})"
            params = {f"doctor_id_{i}": doctor_id for i, doctor_id in enumerate(doctor_ids_int)}

        sql_query_text = f"""
            SELECT DISTINCT MONTH(s.StartDateTime) AS AvailableMonthNum
            FROM medirect.dbo.MEDirectBookingCalendar c
            INNER JOIN medirect.dbo.MEDirectBookingSlot s ON c.Id = s.CalendarId
            INNER JOIN medirect.dbo.MEDirectUserAccount u ON c.UserId = u.Id
            LEFT JOIN medirect.dbo.MEDirectBranch mb On mb.id = c.BranchId
            WHERE mb.Name LIKE '%HSA%' AND s.IsBooked = 0
            {doctor_ids_clause}
            ORDER BY AvailableMonthNum
        """
        sql_query = text(sql_query_text)
        result = db.session.execute(sql_query, params).fetchall()
        available_months_nums = sorted({row.AvailableMonthNum for row in result})
        available_months = [cal.month_abbr[num] for num in available_months_nums if num != 0]

        return jsonify(available_months)
    except Exception as e:
        app.logger.error(f"Error fetching available months: {e}")
        return jsonify({'error': 'Error fetching available months'}), 500
    
@app.route('/api/available-years', methods=['GET'])
def get_available_years():
    try:
        # SQL query to select distinct years from the start dates of bookings
        sql_query = text("""
            SELECT DISTINCT YEAR(StartDateTime) AS Year
            FROM medirect.dbo.MEDirectBookingSlot
            WHERE IsBooked = 1 AND YEAR(StartDateTime) >= YEAR(CURRENT_TIMESTAMP)
            ORDER BY Year
        """)

        # Execute the query
        result = db.session.execute(sql_query).fetchall()

        # Extract the years from the result and convert to a list of integers
        # Use 'row.Year' if the result is accessed by attribute
        available_years = [row.Year for row in result]

        # Return a JSON list of years
        return jsonify(available_years)
    except Exception as e:
        # If an error occurs, return an error message and a 500 status code
        app.logger.error(f"An error occurred when fetching available years: {e}")
        return jsonify({'error': 'Unable to fetch available years'}), 500

# Helper function to increment the reference ID
def increment_id(last_id):
    match = re.match(r"(BREF)(\d+)", last_id)
    if match:
        prefix = match.group(1)
        id_number = int(match.group(2))
        return f"{prefix}{str(id_number + 1).zfill(4)}"
    else:
        raise ValueError(f"Invalid ID format: {last_id}")

@app.route('/api/get-latest-reference-id', methods=['GET'])
def get_latest_reference_id():
    path_to_file = os.path.join(current_app.root_path, 'reference_ids.txt')
    try:
        if not os.path.isfile(path_to_file):
            # If file does not exist, start with BREF0001
            return jsonify({'latest_reference_id': 'BREF0001'}), 200

        with open(path_to_file, 'r') as file:
            lines = file.readlines()
            last_id = lines[-1].strip() if lines else 'BREF0000'
            next_id = increment_id(last_id)
            return jsonify({'latest_reference_id': next_id}), 200


    except ValueError as ve:
        app.logger.error(f'Invalid format in reference ID: {ve}')
        return jsonify({'error': 'Invalid reference ID format'}), 500
    except Exception as e:
        app.logger.error(f'An unexpected error occurred: {e}')
        return jsonify({'error': str(e)}), 500

    
# Helper function to read and increment the reference ID
def get_next_reference_id():
    ref_id_path = 'last_ref_id.txt'  # Path to a file storing the last reference ID
    base_id = 'BREF'
    
    # If the file doesn't exist, initialize the ID
    if not os.path.exists(ref_id_path):
        last_id = 0
    else:
        with open(ref_id_path, 'r') as file:
            last_id = int(file.read().strip().replace(base_id, ''))
    
    # Increment the ID
    next_id = last_id + 1
    
    # Write the new ID back to the file
    with open(ref_id_path, 'w') as file:
        file.write(f"{base_id}{next_id:04d}")
    
    # Return the new reference ID
    return f"{base_id}{next_id:04d}"

@app.route('/api/send-booking-email', methods=['POST'])
def send_booking_email():
    try:
        # Parse request data
        data = request.json
        patient_name = data.get('patient_name')
        patient_email = data.get('email')
        patient_phone = data.get('phone')
        company_location = data.get('company_location')
        suburb = data.get('suburb')
        medical_expert = data.get('doctor_name')
        examinee_name = data.get('examinee_name')  # Optional
        examinee_ref_number = data.get('examinee_ref_number')  # Optional
        appointment_time = data.get('appointment_time')
        reference_id = get_next_reference_id()  # Fetch the next available reference ID


        # Acquire an access token
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        token_data = {
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
            "client_id": client_id,
            "client_secret": client_secret
        }
        token_response = requests.post(token_url, data=token_data).json()
        access_token = token_response.get("access_token")

        # Construct the email subject and body with dynamic data
        subject = f"New HSA Appointment Request: {reference_id} - {medical_expert}"
        body_content = f"""
            <html>
                <body>
                    <p>Dear {patient_name},</p>
                    <p>Thank you for reaching out. We've successfully received your HSA appointment request. The HSA Booking team is currently reviewing your details and will reach out to you shortly to confirm this appointment.</p>
                    <p><strong>Appointment Request ID:</strong> {reference_id}<br>
                       <strong>Name:</strong> {patient_name}<br>
                       <strong>Email:</strong> {patient_email}<br>
                       <strong>Phone Number:</strong> {patient_phone}<br>
                       <strong>Company and Office Locations:</strong> {company_location}<br>
                       <strong>Suburb:</strong> {suburb}<br>
                       <strong>Medical Expert:</strong> {medical_expert}<br>
                       <strong>Client's Name:</strong> {examinee_name}<br>
                       <strong>Client's Reference Number:</strong> {examinee_ref_number}<br>
                       <strong>Appointment Date & Time:</strong> {appointment_time}</p>
                    <p>We appreciate your patience and look forward to speaking with you soon.</p>
                    <p>Best regards,<br>
                    The HSA Booking Team</p>
                </body>
            </html>
        """

        # Construct the email JSON with HTML content type
        email_json = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body_content
                },
                "toRecipients": [
                    {"emailAddress": {"address": patient_email}}
                ],
                "ccRecipients": [
                    {"emailAddress": {"address": "hsabookings@medirect.com.au"}}
                ]
            },
            "saveToSentItems": "true"
        }

        # Send the email
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-type": "application/json"
        }
        url_send = f"https://graph.microsoft.com/v1.0/users/{MAIL_USERNAME}/sendMail"
        response = requests.post(url_send, headers=headers, json=email_json)

        # Save the reference ID to a file
        with open('reference_ids.txt', 'a') as file:
            file.write(f"{reference_id}\n")

        # Check response and return appropriate message
        if response.status_code == 202:
            return jsonify({"message": "Email sent successfully!", "reference_id": reference_id}), 202
        else:
            app.logger.error(f"Error sending email. Status code: {response.status_code}")
            return jsonify({'error': 'Error sending email', 'details': response.text}), response.status_code

    except Exception as e:
        # Log and respond with the error
        app.logger.exception('Failed to send email.')
        return jsonify({'error': 'Failed to send email', 'details': str(e)}), 500


@app.route('/')
def calendar():
    return app.send_static_file('calendar.html')

if __name__ == '__main__':
    app.run(debug=True)

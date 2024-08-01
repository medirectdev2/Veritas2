import calendar as cal
import requests
import re
import os
import logging
import pytz
from flask import Flask, request, jsonify, current_app, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime  # Step 1: Import timedelta

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

booking_urls = {
    "Heng Tan": "https://bookings.medirect.com.au/MDLogin.aspx?next=booking",
    "Iyad Dayoub": "https://bookings.medirect.com.au/MDLogin.aspx?next=booking",
    "Tapuwa Musuka": "https://bookings.medirect.com.au/new?n=tapuwamusuka",
    "Siamak Seresti": "https://bookings.medirect.com.au/new?n=siamakseresti",
    "Nicole Leeks": "https://bookings.medirect.com.au/new?n=nicoleleeks",
    "Olivia Lee": "https://bookings.medirect.com.au/new?n=olivialee",
    "Matthew Samuel": "https://bookings.medirect.com.au/new?n=mathewsamuel",
    "Reza Feizerfan": "https://bookings.medirect.com.au/new?n=rezafeizerfan",
    "David Colvin": "https://bookings.medirect.com.au/new?n=davidcolvin",
    "Jessica Johnson": "https://bookings.medirect.com.au/new?n=jessicajohnson",
    "Andrew Thomson": "https://bookings.medirect.com.au/new?n=andrewthomson"

}

# Mapping of doctor names to their WordPress page URLs
doctor_links = {
    "Heng Tan": "https://medirect.com.au/drhengtan/",
    "Iyad Dayoub": "https://medirect.com.au/driyaddayoub/",
    "Tapuwa Musuka": "https://medirect.com.au/drtapuwamusuka/",
    "Siamak Seresti": "https://medirect.com.au/mrsiamakseresti/",
    "Nicole Leeks": "https://medirect.com.au/drnicoleleeks/",
    "Olivia Lee": "https://medirect.com.au/drolivialee/",
    "Matthew Samuel": "https://medirect.com.au/drmathewsamuel/",
    "Reza Feizerfan": "https://medirect.com.au/drrezafeizerfan/",
    "David Colvin": "https://medirect.com.au/mrdavidcolvin/",
    "Jessica Johnson": "https://medirect.com.au/drjessicajohnson/",
    "Andrew Thomson": "https://medirect.com.au/drandrewthomson/"
}

# Simple incremental reference ID generator (for example purposes only)
ref_id_counter = 1

# A helper function to map month numbers to names
def month_number_to_name(month_num):
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return month_names[month_num - 1] if 1 <= month_num <= 12 else None

# Endpoint to get booking URL based on doctor's name
@app.route('/api/booking-url', methods=['GET'])
def get_booking_url():
    doctor_name = request.args.get('doctor')
    if doctor_name in booking_urls:
        return jsonify({'bookingUrl': booking_urls[doctor_name]})
    else:
        return jsonify({'error': 'Doctor not found'}), 404

@app.route('/api/doctor-link', methods=['GET'])
def get_doctor_link():
    doctor_name = request.args.get('doctor')
    if doctor_name in doctor_links:
        return jsonify({'doctorLink': doctor_links[doctor_name]})
    else:
        return jsonify({'error': 'Doctor not found'}), 404

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    # Define your SQL query using a Common Table Expression (CTE)
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
		WHERE u.Id IN (8562, 8567, 8566, 8565, 8560,8561,8535,8533,8613,8678,8677)
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
@app.route('/api/all_doctors', methods=['GET'])
def get_all_doctors():
    # Define your SQL query using a Common Table Expression (CTE)
    sql_query = text("""
        SELECT DISTINCT 
            u.FirstName + ' ' + u.LastName AS FullName,
            u.Email,
            u.Position,
            u.Id AS DoctorID
        FROM medirect.dbo.MEDirectBookingCalendar c
        INNER JOIN medirect.dbo.MEDirectBookingSlot s ON c.Id = s.CalendarId
        INNER JOIN medirect.dbo.MEDirectUserAccount u ON c.UserId = u.Id
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
        app.logger.error(f"An error occurred when fetching all doctors: {e}")
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
            END as AppointmentStatus
        FROM medirect.dbo.MEDirectBookingCalendar c
        INNER JOIN medirect.dbo.MEDirectBookingSlot s ON c.Id = s.CalendarId
        INNER JOIN medirect.dbo.MEDirectUserAccount u ON c.UserId = u.Id
        INNER JOIN medirect.dbo.MEDirectBranch b ON c.BranchId = b.Id
        LEFT JOIN medirect.dbo.MEDirectCaseService cs On s.CaseId = cs.Id
        LEFT JOIN medirect.dbo.MEDirectBranch mb On mb.id = c.BranchId
        WHERE u.Id IN (8562, 8567, 8566, 8565, 8560,8561,8535,8533,8613,8678,8677) and s.IsBooked = 0
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



@app.route('/')
def calendar():
    return render_template('calendar2.html')

if __name__ == '__main__':
    # Get the port number from the environment variable (default to 8000)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
    

from flask import Blueprint, jsonify
from sqlalchemy import text
from app import db  # Make sure this points to your initialized SQLAlchemy instance

doctor_calendar = Blueprint('doctor_calendar', __name__)

@doctor_calendar.route('/api/doctor-calendar', methods=['GET'])
def get_doctor_calendar():
    sql = text("""
    WITH ActiveSlots AS (
        SELECT 
            u.FirstName + ' ' + u.LastName AS FullName,
            u.Email,
            s.CaseId,
            b.State,
            CONCAT(b.Address1, ', ', b.City, ' ', b.Postcode) AS Position,
            b.Lat,
            b.Lng,
            b.Postcode,
            s.StartDateTime,
            s.EndDateTime,
            cs.ServiceName,
            u.Id AS DoctorID,
            d.MDReportDue,
            CASE 
                WHEN s.IsBooked = 0 THEN 'Not Booked' 
                WHEN s.IsBooked = 1 THEN 'Booked' 
                ELSE 'Inactive' 
            END AS AppointmentStatus
        FROM medirect.dbo.MEDirectBookingCalendar c
        INNER JOIN medirect.dbo.MEDirectBookingSlot s ON c.Id = s.CalendarId
        INNER JOIN medirect.dbo.MEDirectUserAccount u ON c.UserId = u.Id
        INNER JOIN medirect.dbo.MEDirectBranch b ON c.BranchId = b.Id
        LEFT JOIN medirect.dbo.MEDirectCaseService cs ON s.CaseId = cs.Id
        LEFT JOIN medirect.dbo.MEDirectCase d ON d.Id = s.CaseId
    )

    SELECT 
        FORMAT(StartDateTime, 'yyyy-MM-dd') AS AppointmentDate,
        DoctorID,
        FullName,
        Email,
        State,
        Position,
        Postcode,
        ServiceName,
        AppointmentStatus,
        COUNT(*) AS SlotCount
    FROM ActiveSlots
    WHERE StartDateTime >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)
    GROUP BY 
        FORMAT(StartDateTime, 'yyyy-MM-dd'),
        DoctorID,
        FullName,
        Email,
        State,
        Position,
        Postcode,
        ServiceName,
        AppointmentStatus
    ORDER BY AppointmentDate, FullName;
    """)

    try:
        result = db.session.execute(sql).fetchall()
        output = [
            {
                "appointment_date": row.AppointmentDate,
                "doctor_id": row.DoctorID,
                "doctor_name": row.FullName,
                "email": row.Email,
                "state": row.State,
                "location": row.Position,
                "postcode": row.Postcode,
                "service": row.ServiceName,
                "status": row.AppointmentStatus,
                "slot_count": int(row.SlotCount)
            }
            for row in result
        ]
        return jsonify(output)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

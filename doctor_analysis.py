# doctor_analysis.py
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from app import db

doctor_analysis = Blueprint('doctor_analysis', __name__)

@doctor_analysis.route('/api/doctor-analysis', methods=['GET'])
def get_doctor_analysis():
    year = request.args.get('year', type=int)
    quarter = request.args.get('quarter', type=int)
    month = request.args.get('month', type=int)
    doctor_id = request.args.get('doctor_id', type=int)

    conditions = []
    params = {}

    # Default to current year if no year is provided
    if year:
        conditions.append("YEAR(InvoiceDate) = :year")
        params["year"] = year
    else:
        conditions.append("YEAR(InvoiceDate) = YEAR(GETDATE())")

    if quarter:
        conditions.append("DATEPART(QUARTER, InvoiceDate) = :quarter")
        params["quarter"] = quarter

    if month:
        conditions.append("MONTH(InvoiceDate) = :month")
        params["month"] = month

    if doctor_id:
        conditions.append("T6.Id = :doctor_id")
        params["doctor_id"] = doctor_id

    where_clause = " AND ".join(conditions)

    sql = text(f"""
    WITH InvoiceDetails AS (
        SELECT 
            T1.Id,
            T1.InvoiceDate,
            T1.IsActive,
            TRIM(T6.FirstName + ' ' + T6.LastName) AS [Medical Expert],
            T6.Id AS DoctorID,
            CAST(T1.TotalEx AS float) / 100 AS [AmountExGST],
            CAST(T1.TotalInc AS float) / 100 AS [AmountIncGST],
            CAST(T1.TotalGST AS float) / 100 AS [GST],
            CAST(ISNULL(T9.AmountPaid, 0) AS float) / 100 AS [AmountPaid]
        FROM medirect.dbo.MEDirectCaseInvoice AS T1
        LEFT JOIN medirect.dbo.MEDirectCase AS T4 ON T4.CaseNo = T1.CaseNo
        LEFT JOIN medirect.dbo.MEDirectUserAccount AS T6 ON T6.Id = T4.CaseWorkerId
        LEFT JOIN medirect.dbo.MEDirectCasePaidInvoice AS T9 ON T9.InvoiceId = T1.Id
        WHERE T1.IsActive = 1 AND {where_clause}
    ),

    Aggregated AS (
        SELECT 
            [DoctorID],
            [Medical Expert],
            SUM([AmountExGST]) AS TotalExGST,
            SUM([AmountIncGST]) AS TotalIncGST,
            SUM([GST]) AS TotalGST,
            SUM([AmountPaid]) AS TotalPaid,
            SUM([AmountPaid]) - SUM([AmountIncGST]) AS BalanceOrOverpaid,
            COUNT(*) AS TotalInvoices
        FROM InvoiceDetails
        GROUP BY [DoctorID], [Medical Expert]
    ),

    AllTotal AS (
        SELECT 
            SUM([AmountExGST]) AS AllTotalExGST,
            COUNT(*) AS AllInvoices
        FROM InvoiceDetails
    )

    SELECT 
        A.DoctorID,
        A.[Medical Expert],
        A.TotalExGST,
        A.TotalIncGST,
        A.TotalGST,
        A.TotalPaid,
        A.BalanceOrOverpaid,
        A.TotalInvoices,
        CAST(A.TotalInvoices AS float) / NULLIF(AT.AllInvoices, 0) * 100 AS PercentOfInvoices,
        CAST(A.TotalExGST AS float) / NULLIF(AT.AllTotalExGST, 0) * 100 AS PercentOfOverallRevenue
    FROM Aggregated A
    CROSS JOIN AllTotal AT
    ORDER BY A.TotalExGST DESC;
    """)

    try:
        result = db.session.execute(sql, params).mappings().fetchall()

        response = [
            {
                "doctor_id": row["DoctorID"],
                "medical_expert": row["Medical Expert"],
                "total_exc_gst": float(row["TotalExGST"]),
                "total_inc_gst": float(row["TotalIncGST"]),
                "total_gst": float(row["TotalGST"]),
                "amount_paid": float(row["TotalPaid"]),
                "balance_or_overpayment": float(row["BalanceOrOverpaid"]),
                "invoice_count": int(row["TotalInvoices"]),
                "percent_of_invoices": round(row["PercentOfInvoices"] or 0, 2),
                "percent_of_total_revenue": round(row["PercentOfOverallRevenue"] or 0, 2)
            }
            for row in result
        ]
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

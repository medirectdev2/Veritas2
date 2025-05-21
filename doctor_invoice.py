from flask import Blueprint, jsonify
from sqlalchemy import text
from app import db  # Assumes `db` is defined in app.py

doctor_invoice = Blueprint('doctor_invoice', __name__)

@doctor_invoice.route('/api/doctor-invoice', methods=['GET'])
def get_doctor_invoice_summary():
    sql = text("""
    WITH InvoiceDetails AS (
        SELECT 
            T1.[Id],
            T1.CaseId AS [Case ID],
            T1.InvoiceNo AS [Invoice No],
            T1.Attn AS [Attn],
            T1.ToAddress AS [To Address],
            T1.Client AS [Case],
            T1.CaseManager AS [Case Manager],
            T1.ClaimNo AS [Claim No],
            T1.CaseNo AS [Case No],
            T1.Employer AS [Employer],
            T1.ReferralDate AS [Referral Date],
            T1.InvoiceDate AS [Invoice Date],
            T1.IsActive,
            CAST(T1.TotalEx AS float) / 100 AS [Amount (ex GST)],
            TRIM(T6.FirstName + ' ' + T6.LastName) AS [Medical Expert],
            T5.Name AS [Sectors and Schemes],
            TRIM(T3.OrganisationName) AS [Organisation Name],
            T8.Name AS [Contact Category]
        FROM medirect.dbo.MEDirectCaseInvoice AS T1
        LEFT JOIN medirect.dbo.MEDirectContact AS T2 ON T2.Id = T1.BillToContactId
        LEFT JOIN medirect.dbo.MEDirectOrganisation AS T3 ON T3.Id = T2.OrganisationId
        LEFT JOIN medirect.dbo.MEDirectCase AS T4 ON T4.CaseNo = T1.CaseNo
        LEFT JOIN medirect.dbo.MEDirectCaseType AS T5 ON T5.Id = T4.CaseTypeId
        LEFT JOIN medirect.dbo.MEDirectUserAccount AS T6 ON T6.Id = T4.CaseWorkerId
        LEFT JOIN medirect.dbo.MEDirectContactCategory AS T8 ON T8.Id = T2.DefaultContactCategoryId
    )

    SELECT
        FORMAT([Invoice Date], 'yyyy-MM') AS [Invoice Month],
        [Medical Expert],
        [Contact Category],
        [Sectors and Schemes],
        [Organisation Name],
        SUM([Amount (ex GST)]) AS [Total Inv Ex GST]
    FROM InvoiceDetails
    WHERE 
        [Invoice Date] >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1)
        AND IsActive = 1
    GROUP BY
        FORMAT([Invoice Date], 'yyyy-MM'),
        [Medical Expert],
        [Contact Category],
        [Sectors and Schemes],
        [Organisation Name]
    ORDER BY 
        [Invoice Month], [Total Inv Ex GST] DESC;
    """)

    try:
        result = db.session.execute(sql).fetchall()
        output = [
            {
                "month": row[0],
                "medical_expert": row[1],
                "contact_category": row[2],
                "sector_scheme": row[3],
                "organisation": row[4],
                "total_invoice_exc_gst": float(row[5]) if row[5] is not None else 0
            }
            for row in result
        ]
        return jsonify(output)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

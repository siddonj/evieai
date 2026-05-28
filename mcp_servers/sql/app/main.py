"""SQL MCP server — wraps DAB REST API and exposes /mcp/query with demo fallback."""
from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mcp-sql", version="0.3.0")

DAB_BASE = os.getenv("DAB_BASE_URL", "http://localhost:5000")

# ─── Rich Demo Data — Multifamily & Brokerage ───────────────────────

_DEMO_PROPERTIES = [
    {"id": 1, "name": "The Vue at Madison", "address": "123 Madison Ave", "city": "Memphis", "state": "TN", "zip": "38103", "property_type": "Multifamily", "total_units": 240, "year_built": 2018, "building_size_sqft": 210000, "lot_size_acres": 3.2, "units_occupied": 228, "average_rent": 1625.00, "noi": 1872000, "cap_rate": 5.8, "estimated_value": 32275862, "owner": "Madison Street Partners", "property_manager": "Pinnacle Property Management", "status": "Active"},
    {"id": 2, "name": "Riverside Heights", "address": "800 Riverside Blvd", "city": "Memphis", "state": "TN", "zip": "38103", "property_type": "Multifamily", "total_units": 180, "year_built": 2015, "building_size_sqft": 158000, "lot_size_acres": 2.8, "units_occupied": 171, "average_rent": 1475.00, "noi": 1380000, "cap_rate": 5.5, "estimated_value": 25090909, "owner": "Riverside Capital Group", "property_manager": "Greystar Management", "status": "Active"},
    {"id": 3, "name": "Oakwood Crossings", "address": "4525 Oakwood Dr", "city": "Memphis", "state": "TN", "zip": "38117", "property_type": "Multifamily", "total_units": 96, "year_built": 1985, "building_size_sqft": 72000, "lot_size_acres": 5.1, "units_occupied": 82, "average_rent": 1095.00, "noi": 648000, "cap_rate": 6.2, "estimated_value": 10451613, "owner": "Oakwood Holdings LLC", "property_manager": "Self-managed", "status": "Active"},
    {"id": 4, "name": "Highland Ridge", "address": "3200 Highland Ave", "city": "Memphis", "state": "TN", "zip": "38111", "property_type": "Multifamily", "total_units": 64, "year_built": 1978, "building_size_sqft": 48000, "lot_size_acres": 3.5, "units_occupied": 58, "average_rent": 975.00, "noi": 384000, "cap_rate": 6.8, "estimated_value": 5647059, "owner": "Highland Properties LLC", "property_manager": "Self-managed", "status": "Active"},
    {"id": 5, "name": "The Emerson", "address": "150 Court Ave", "city": "Memphis", "state": "TN", "zip": "38103", "property_type": "Multifamily", "total_units": 312, "year_built": 2021, "building_size_sqft": 285000, "lot_size_acres": 1.8, "units_occupied": 296, "average_rent": 1895.00, "noi": 3450000, "cap_rate": 5.2, "estimated_value": 66346154, "owner": "Emerson Development Group", "property_manager": "Cushman & Wakefield", "status": "Active"},
    {"id": 6, "name": "Southgate Village", "address": "782 South Parkway E", "city": "Memphis", "state": "TN", "zip": "38106", "property_type": "Multifamily", "total_units": 128, "year_built": 1972, "building_size_sqft": 86000, "lot_size_acres": 4.2, "units_occupied": 102, "average_rent": 845.00, "noi": 480000, "cap_rate": 7.5, "estimated_value": 6400000, "owner": "Southgate REIT", "property_manager": "FirstService Residential", "status": "Active"},
    {"id": 7, "name": "Poplar Pointe", "address": "6280 Poplar Ave", "city": "Memphis", "state": "TN", "zip": "38119", "property_type": "Multifamily", "total_units": 72, "year_built": 1998, "building_size_sqft": 54000, "lot_size_acres": 2.1, "units_occupied": 68, "average_rent": 1280.00, "noi": 560000, "cap_rate": 5.9, "estimated_value": 9491525, "owner": "Poplar Pointe Investors", "property_manager": "Mid-South Property Group", "status": "Active"},
    {"id": 8, "name": "Village at Germantown", "address": "9122 Exeter Rd", "city": "Germantown", "state": "TN", "zip": "38138", "property_type": "Multifamily", "total_units": 156, "year_built": 2005, "building_size_sqft": 130000, "lot_size_acres": 6.8, "units_occupied": 148, "average_rent": 1475.00, "noi": 1248000, "cap_rate": 5.4, "estimated_value": 23111111, "owner": "Germantown Development LLC", "property_manager": "BH Management", "status": "Under Contract"},
    {"id": 9, "name": "University Village", "address": "3500 Alumni Ave", "city": "Memphis", "state": "TN", "zip": "38152", "property_type": "Student Housing", "total_units": 120, "year_built": 1975, "building_size_sqft": 72000, "lot_size_acres": 4.8, "units_occupied": 112, "average_rent": 725.00, "noi": 396000, "cap_rate": 7.0, "estimated_value": 5657143, "owner": "U of M Properties LLC", "property_manager": "Campus Living Solutions", "status": "Active"},
    {"id": 10, "name": "The Gardens at Shelby", "address": "7800 Poplar Pike", "city": "Memphis", "state": "TN", "zip": "38125", "property_type": "Senior Living", "total_units": 90, "year_built": 2008, "building_size_sqft": 68000, "lot_size_acres": 3.2, "units_occupied": 86, "average_rent": 2100.00, "noi": 856000, "cap_rate": 6.5, "estimated_value": 13169231, "owner": "Shelby Senior Housing Fund", "property_manager": "Legacy Senior Living", "status": "Active"},
    {"id": 11, "name": "Court Square Flats", "address": "10 N Main St", "city": "Memphis", "state": "TN", "zip": "38103", "property_type": "Mixed-Use", "total_units": 24, "year_built": 1920, "building_size_sqft": 28000, "lot_size_acres": 0.3, "units_occupied": 22, "average_rent": 1550.00, "noi": 186000, "cap_rate": 5.5, "estimated_value": 3381818, "owner": "Court Square Development LLC", "property_manager": "Downtown Property Group", "status": "Active"},
    {"id": 12, "name": "Cordova Station", "address": "1050 N Germantown Pkwy", "city": "Cordova", "state": "TN", "zip": "38018", "property_type": "Multifamily", "total_units": 168, "year_built": 2001, "building_size_sqft": 125000, "lot_size_acres": 7.5, "units_occupied": 154, "average_rent": 1185.00, "noi": 1008000, "cap_rate": 5.8, "estimated_value": 17379310, "owner": "Cordova Station Partners", "property_manager": "RPM Management", "status": "Active"},
]

_DEMO_CONTACTS = [
    {"id": 1, "first_name": "Robert", "last_name": "Henderson", "email": "rhenderson@madisonstreet.com", "phone": "901-555-0101", "company": "Madison Street Partners", "job_title": "Managing Partner", "role": "Owner", "property_id": 1, "notes": "Acquired The Vue in 2019. Looking to expand portfolio in downtown Memphis."},
    {"id": 2, "first_name": "Sarah", "last_name": "Mitchell", "email": "smitchell@greystar.com", "phone": "901-555-0102", "company": "Greystar Management", "job_title": "Senior Property Manager", "role": "Property Manager", "property_id": 2, "notes": "Oversees Riverside Heights portfolio. 15 years MF experience."},
    {"id": 3, "first_name": "James", "last_name": "Campbell", "email": "jcampbell@oakwoodholdings.com", "phone": "901-555-0103", "company": "Oakwood Holdings LLC", "job_title": "Principal", "role": "Owner", "property_id": 3, "notes": "Small-balance investor with 4 properties in Memphis. Active buyer for value-add deals."},
    {"id": 4, "first_name": "Linda", "last_name": "Thornton", "email": "lthornton@cushwake.com", "phone": "901-555-0104", "company": "Cushman & Wakefield", "job_title": "Managing Director", "role": "Broker", "property_id": None, "notes": "Top-producing MF broker in Memphis. $120M+ in transactions last 12 months."},
    {"id": 5, "first_name": "Michael", "last_name": "Davidson", "email": "mdavidson@southgatereit.com", "phone": "901-555-0105", "company": "Southgate REIT", "job_title": "VP of Acquisitions", "role": "Investor", "property_id": 6, "notes": "REIT targeting workforce housing in secondary markets. $50M annual acquisition budget."},
    {"id": 6, "first_name": "Patricia", "last_name": "Wong", "email": "pwong@emersongroup.com", "phone": "901-555-0106", "company": "Emerson Development Group", "job_title": "CEO", "role": "Owner", "property_id": 5, "notes": "Developer of The Emerson. Currently scoping next downtown project."},
    {"id": 7, "first_name": "David", "last_name": "Reynolds", "email": "dreynolds@poplarpointe.com", "phone": "901-555-0107", "company": "Poplar Pointe Investors", "job_title": "General Partner", "role": "Owner", "property_id": 7, "notes": "Syndicator focused on East Memphis. Raised $4.2M for Poplar Pointe acquisition."},
    {"id": 8, "first_name": "Amanda", "last_name": "Foster", "email": "afoster@bhmanagement.com", "phone": "901-555-0108", "company": "BH Management", "job_title": "Regional Director", "role": "Property Manager", "property_id": 8, "notes": "Manages 5 properties in the Mid-South region. 20 years experience."},
    {"id": 9, "first_name": "Thomas", "last_name": "Garrett", "email": "tgarrett@transwestern.com", "phone": "901-555-0109", "company": "Transwestern", "job_title": "Senior Director", "role": "Broker", "property_id": None, "notes": "Specializes in investment sales. Currently marketing 3 MF assets in TN."},
    {"id": 10, "first_name": "Jennifer", "last_name": "Coleman", "email": "jcoleman@firstservice.com", "phone": "901-555-0110", "company": "FirstService Residential", "job_title": "Portfolio Manager", "role": "Property Manager", "property_id": 6, "notes": "Manages Southgate and 2 other workforce housing properties."},
    {"id": 11, "first_name": "Marcus", "last_name": "Williams", "email": "mwilliams@highlandprop.com", "phone": "901-555-0111", "company": "Highland Properties LLC", "job_title": "Owner/Operator", "role": "Owner", "property_id": 4, "notes": "Small owner-operator. Owns Highland Ridge and one other property near U of M."},
    {"id": 12, "first_name": "Angela", "last_name": "Price", "email": "aprice@meridiancap.com", "phone": "901-555-0112", "company": "Meridian Capital Group", "job_title": "Senior Analyst", "role": "Lender", "property_id": None, "notes": "Debt placement specialist. Arranged financing for 3 MF deals in 2025 ($28M total)."},
    {"id": 13, "first_name": "Brian", "last_name": "Foster", "email": "bfoster@firsthorizon.com", "phone": "901-555-0113", "company": "First Horizon Bank", "job_title": "VP Commercial Lending", "role": "Lender", "property_id": None, "notes": "Primary lender for 4 of our portfolio properties. $45M in active MF loans."},
    {"id": 14, "first_name": "Karen", "last_name": "Sims", "email": "ksims@adamsreese.com", "phone": "901-555-0114", "company": "Adams & Reese LLP", "job_title": "Partner", "role": "Attorney", "property_id": None, "notes": "Real estate transactions and due diligence counsel. Handled all 3 Q1-Q2 closings."},
    {"id": 15, "first_name": "Derek", "last_name": "Jackson", "email": "djackson@cbrevaluation.com", "phone": "901-555-0115", "company": "CBRE Valuation", "job_title": "Senior Appraiser", "role": "Appraiser", "property_id": None, "notes": "Lead appraiser for Memphis MF market. 20+ years experience."},
    {"id": 16, "first_name": "Maria", "last_name": "Gonzalez", "email": "mgonzalez@gonzalezconstruction.com", "phone": "901-555-0116", "company": "Gonzalez Construction", "job_title": "President", "role": "Contractor", "property_id": None, "notes": "Preferred GC for value-add renovations. Completed 4 property renovations in 2025."},
    {"id": 17, "first_name": "Steven", "last_name": "Cole", "email": "scole@regions.com", "phone": "901-555-0117", "company": "Regions Bank", "job_title": "SVP Commercial Real Estate", "role": "Lender", "property_id": None, "notes": "Opened $32M credit facility for Emerson acquisition. Relationship banker for 5 MF owners."},
    {"id": 18, "first_name": "Rachel", "last_name": "Bennett", "email": "rbennett@harborgroup.com", "phone": "901-555-0118", "company": "Harbor Group International", "job_title": "Director of Acquisitions", "role": "Investor", "property_id": None, "notes": "HGI actively seeking Memphis MF acquisitions. Target $20-75M, Class A. $500M dry powder."},
    {"id": 19, "first_name": "Chris", "last_name": "Walker", "email": "cwalker@walkerinspections.com", "phone": "901-555-0119", "company": "Walker Property Inspections", "job_title": "Owner", "role": "Inspector", "property_id": None, "notes": "Licensed home inspector. Performed all Phase I and property condition assessments for our listings."},
    {"id": 20, "first_name": "Jonathan", "last_name": "Reed", "email": "jreed@jll.com", "phone": "901-555-0120", "company": "JLL Capital Markets", "job_title": "Managing Director", "role": "Broker", "property_id": None, "notes": "Competing broker for institutional MF mandates. Known Blackstone and Invesco relationships."},
]

_DEMO_DEALS = [
    {"id": 1, "property_id": 8, "deal_type": "Sale", "stage": "Closing", "buyer": "Warburg Realty Trust", "seller": "Germantown Development LLC", "buyer_agent": "Linda Thornton", "seller_agent": "Thomas Garrett", "offer_price": 24500000, "proposed_cap_rate": 5.25, "list_price": 25800000, "days_on_market": 42, "loa_date": "2026-03-15", "due_diligence_deadline": "2026-05-01", "closing_target_date": "2026-07-15", "commission_percentage": 3.0, "commission_total": 735000, "status": "Active", "notes": "Full commission at 3%. Both sides represented. Title work underway."},
    {"id": 2, "property_id": 1, "deal_type": "Sale", "stage": "Due Diligence", "buyer": "Blackstone Real Estate", "seller": "Madison Street Partners", "buyer_agent": "Linda Thornton", "seller_agent": "Thomas Garrett", "offer_price": 34000000, "proposed_cap_rate": 5.5, "list_price": 35800000, "days_on_market": 28, "loa_date": "2026-04-10", "due_diligence_deadline": "2026-06-15", "closing_target_date": "2026-08-30", "commission_percentage": 2.5, "commission_total": 850000, "status": "Active", "notes": "Largest deal in pipeline. Buyer doing extensive Phase I and structural inspection."},
    {"id": 3, "property_id": 3, "deal_type": "Sale", "stage": "LOI", "buyer": "ValueAdd Equity Fund III", "seller": "Oakwood Holdings LLC", "buyer_agent": "Michael Davidson", "seller_agent": "Linda Thornton", "offer_price": 11500000, "proposed_cap_rate": 6.0, "list_price": 12500000, "days_on_market": 14, "loa_date": "2026-05-01", "due_diligence_deadline": "2026-06-30", "closing_target_date": "2026-09-15", "commission_percentage": 3.0, "commission_total": 345000, "status": "Active", "notes": "LOI signed. Buyer touring next week. Value-add play with renovation plan."},
    {"id": 4, "property_id": 5, "deal_type": "Sale", "stage": "LOI", "buyer": "Invesco Real Estate", "seller": "Emerson Development Group", "buyer_agent": "Linda Thornton", "seller_agent": "Thomas Garrett", "offer_price": 68000000, "proposed_cap_rate": 5.0, "list_price": 72000000, "days_on_market": 21, "loa_date": "2026-04-28", "due_diligence_deadline": "2026-07-01", "closing_target_date": "2026-10-01", "commission_percentage": 2.0, "commission_total": 1360000, "status": "Active", "notes": "Marquee downtown asset. Multiple offers received. Negotiating final terms."},
    {"id": 5, "property_id": 4, "deal_type": "Sale", "stage": "Underwriting", "buyer": "Camber Property Group", "seller": "Highland Properties LLC", "buyer_agent": "Linda Thornton", "seller_agent": "Thomas Garrett", "offer_price": 6200000, "proposed_cap_rate": 6.5, "list_price": 6800000, "days_on_market": 18, "loa_date": "2026-05-10", "due_diligence_deadline": "2026-07-15", "closing_target_date": "2026-10-30", "commission_percentage": 3.5, "commission_total": 217000, "status": "Active", "notes": "Investor pursuing 1031 exchange. Underwriting in progress."},
    {"id": 6, "property_id": 2, "deal_type": "Sale", "stage": "Closed", "buyer": "Warburg Realty Trust", "seller": "Riverside Capital Group", "buyer_agent": "Linda Thornton", "seller_agent": "Thomas Garrett", "offer_price": 26500000, "proposed_cap_rate": 5.3, "list_price": 27500000, "days_on_market": 35, "loa_date": "2026-01-15", "due_diligence_deadline": "2026-03-01", "closing_target_date": "2026-05-01", "commission_percentage": 2.5, "commission_total": 662500, "status": "Closed", "notes": "Closed May 1, 2026. Smooth transaction. Buyer assumed existing management."},
    {"id": 7, "property_id": 7, "deal_type": "Sale", "stage": "Closed", "buyer": "Poplar Pointe Investors", "seller": "Private Seller", "buyer_agent": "Linda Thornton", "seller_agent": "Thomas Garrett", "offer_price": 9800000, "proposed_cap_rate": 5.8, "list_price": 10200000, "days_on_market": 28, "loa_date": "2026-02-01", "due_diligence_deadline": "2026-03-20", "closing_target_date": "2026-05-15", "commission_percentage": 3.0, "commission_total": 294000, "status": "Closed", "notes": "Closed May 15. Syndication deal with 12 LP investors. Exceeded fundraising target."},
    {"id": 8, "property_id": 6, "deal_type": "Sale", "stage": "Lost", "buyer": "N/A", "seller": "Southgate REIT", "buyer_agent": "Michael Davidson", "seller_agent": "Thomas Garrett", "offer_price": 6800000, "proposed_cap_rate": 7.2, "list_price": 7200000, "days_on_market": 45, "loa_date": "2025-12-01", "due_diligence_deadline": "2026-02-01", "closing_target_date": None, "commission_percentage": 2.5, "commission_total": 170000, "status": "Lost", "notes": "REIT decided to hold. Capital allocation shifted to Southeast market."},
    {"id": 9, "property_id": 10, "deal_type": "Lease", "stage": "Negotiating", "buyer": "Shelby Senior Housing Fund", "seller": "Trustee of Shelby County", "buyer_agent": "Linda Thornton", "seller_agent": "Jonathan Reed", "offer_price": 850000, "proposed_cap_rate": 6.25, "list_price": 920000, "days_on_market": 35, "loa_date": "2026-04-20", "due_diligence_deadline": "2026-06-15", "closing_target_date": "2026-08-01", "commission_percentage": 4.0, "commission_total": 34000, "status": "Active", "notes": "Ground lease renewal for The Gardens at Shelby. 99-year lease with 2% annual escalator."},
    {"id": 10, "property_id": 5, "deal_type": "Refinance", "stage": "Underwriting", "buyer": "N/A", "seller": "Emerson Development Group", "buyer_agent": "Linda Thornton", "seller_agent": "N/A", "offer_price": 45000000, "proposed_cap_rate": None, "list_price": 45000000, "days_on_market": 0, "loa_date": "2026-05-05", "due_diligence_deadline": "2026-07-01", "closing_target_date": "2026-08-15", "commission_percentage": 0.5, "commission_total": 225000, "status": "Active", "notes": "Refinancing The Emerson. Current loan maturing Oct 2026. New 10-year fixed at 5.25%."},
    {"id": 11, "property_id": None, "deal_type": "Sale", "stage": "LOI", "buyer": "Pinnacle Development Group", "seller": "Germantown Land Trust", "buyer_agent": "Thomas Garrett", "seller_agent": "Linda Thornton", "offer_price": 3200000, "proposed_cap_rate": None, "list_price": 3800000, "days_on_market": 60, "loa_date": "2026-05-12", "due_diligence_deadline": "2026-07-15", "closing_target_date": "2026-10-01", "commission_percentage": 3.5, "commission_total": 112000, "status": "Active", "notes": "8.2-acre development parcel on Germantown Rd. Entitled for 120-unit MF."},
    {"id": 12, "property_id": None, "deal_type": "Sale", "stage": "LOI", "buyer": "BlueSky Capital Partners", "seller": "Various Sellers", "buyer_agent": "Linda Thornton", "seller_agent": "Thomas Garrett", "offer_price": 14500000, "proposed_cap_rate": 7.0, "list_price": 16000000, "days_on_market": 14, "loa_date": "2026-05-18", "due_diligence_deadline": "2026-07-01", "closing_target_date": "2026-09-30", "commission_percentage": 2.5, "commission_total": 362500, "status": "Active", "notes": "Two-property portfolio: Southgate Village + Highland Ridge. Combined 192 units, $864K NOI."},
]

_DEMO_ACTIVITIES = [
    {"id": 1, "deal_id": 1, "contact_id": None, "activity_type": "Tour", "subject": "Property tour with Blackstone team", "description": "Full walkthrough of The Vue. Inspecting unit finishes, common areas, and mechanicals.", "due_date": "2026-04-12", "completed_at": "2026-04-12T14:30:00", "assigned_to": "Linda Thornton", "status": "Completed"},
    {"id": 2, "deal_id": 3, "contact_id": 3, "activity_type": "Tour", "subject": "ValueAdd Equity tour of Oakwood Crossings", "description": "Buyer team touring property. Focus on recently renovated units and deferred maintenance.", "due_date": "2026-05-15", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 3, "deal_id": 4, "contact_id": None, "activity_type": "Tour", "subject": "Camber Group tour Highland Ridge", "description": "Initial tour with Camber's acquisitions team. Discussing value-add potential near U of M.", "due_date": "2026-05-20", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 4, "deal_id": 2, "contact_id": None, "activity_type": "Inspection", "subject": "Phase I Environmental — The Vue", "description": "Buyer-ordered Phase I environmental assessment.", "due_date": "2026-05-25", "completed_at": None, "assigned_to": "Environmental Partners Inc", "status": "Open"},
    {"id": 5, "deal_id": 2, "contact_id": None, "activity_type": "Inspection", "subject": "Structural engineering review — The Vue", "description": "Review of 2018 construction quality.", "due_date": "2026-05-20", "completed_at": None, "assigned_to": "Southeastern Engineering", "status": "Open"},
    {"id": 6, "deal_id": 1, "contact_id": None, "activity_type": "Inspection", "subject": "Final walkthrough — Village at Germantown", "description": "Pre-closing walkthrough with Warburg team.", "due_date": "2026-06-30", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 7, "deal_id": 2, "contact_id": 1, "activity_type": "Meeting", "subject": "Property tour debrief with Robert Henderson", "description": "Robert wants to discuss 1031 options post-sale.", "due_date": "2026-04-14", "completed_at": "2026-04-14T11:00:00", "assigned_to": "Linda Thornton", "status": "Completed"},
    {"id": 8, "deal_id": 4, "contact_id": 6, "activity_type": "Meeting", "subject": "Listing strategy for The Emerson", "description": "Discussing off-market vs. public listing strategy.", "due_date": "2026-05-10", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 9, "deal_id": 1, "contact_id": None, "activity_type": "Appraisal", "subject": "Appraisal — Village at Germantown", "description": "Lender-ordered appraisal. Expected value range $24-26M.", "due_date": "2026-06-01", "completed_at": None, "assigned_to": "Memphis Appraisal Group", "status": "Open"},
    {"id": 10, "contact_id": 4, "activity_type": "Meeting", "subject": "Q2 business review with Linda", "description": "Reviewing Q2 pipeline ($88M total), closed deals ($12.7M), and Q3 forecasting.", "due_date": "2026-05-22", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 11, "contact_id": 13, "activity_type": "Meeting", "subject": "Lender lunch — First Horizon credit review", "description": "Meeting Brian Foster to discuss 2027 MF lending appetite. Rates expected to drop 50bp.", "due_date": "2026-05-28", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 12, "deal_id": 12, "contact_id": 18, "activity_type": "Tour", "subject": "BlueSky Capital portfolio tour", "description": "Walking Southgate Village and Highland Ridge with BlueSky's acquisitions team.", "due_date": "2026-06-05", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 13, "contact_id": 15, "activity_type": "Inspection", "subject": "Derek Jackson — The Vue appraisal walk", "description": "Accompanying Derek for the appraisal inspection. Providing comps and financial data.", "due_date": "2026-06-08", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 14, "deal_id": 10, "contact_id": 12, "activity_type": "Appraisal", "subject": "Refinance appraisal — The Emerson", "description": "Lender-ordered appraisal for $45M refinance. Coordinating access to all 312 units.", "due_date": "2026-06-15", "completed_at": None, "assigned_to": "Memphis Appraisal Group", "status": "Open"},
    {"id": 15, "contact_id": 19, "activity_type": "Meeting", "subject": "New business lunch — JLL collaboration", "description": "Jonathan Reed wants to discuss co-broke opportunities on future Germantown listings.", "due_date": "2026-06-02", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 16, "contact_id": 18, "activity_type": "Tour", "subject": "Rachel Bennett — Harbor Group property tour", "description": "Harbor Group's Director of Acquisitions in town. Touring The Emerson and The Vue.", "due_date": "2026-06-12", "completed_at": None, "assigned_to": "Linda Thornton", "status": "Open"},
    {"id": 17, "contact_id": 4, "activity_type": "Meeting", "subject": "Weekly deal pipeline review", "description": "12 active deals, $197M total pipeline. Reviewing Q3 targets.", "due_date": "2026-05-19", "completed_at": "2026-05-19T09:00:00", "assigned_to": "Linda Thornton", "status": "Completed"},
]

_DEMO_R1_SITES = [
    {
        "id": 1,
        "site_code": "hq-campus",
        "site_name": "HQ Campus",
        "region": "West",
        "city": "Memphis",
        "state": "TN",
        "isp_primary": "AT&T Business Fiber",
        "isp_secondary": "Comcast Business",
        "sla_target_uptime_pct": 99.95,
    },
    {
        "id": 2,
        "site_code": "dist-north",
        "site_name": "Distribution North",
        "region": "Central",
        "city": "Nashville",
        "state": "TN",
        "isp_primary": "Lumen DIA",
        "isp_secondary": "AT&T Business Fiber",
        "sla_target_uptime_pct": 99.9,
    },
    {
        "id": 3,
        "site_code": "remote-east",
        "site_name": "Remote Branch East",
        "region": "East",
        "city": "Knoxville",
        "state": "TN",
        "isp_primary": "Charter Spectrum Enterprise",
        "isp_secondary": "Lumen DIA",
        "sla_target_uptime_pct": 99.9,
    },
]

_DEMO_R1_DEVICES = [
    {"id": 101, "site_id": 1, "name": "AP-HQ-01", "status": "online"},
    {"id": 102, "site_id": 1, "name": "AP-HQ-02", "status": "online"},
    {"id": 201, "site_id": 2, "name": "AP-DN-01", "status": "online"},
    {"id": 301, "site_id": 3, "name": "AP-RB-01", "status": "degraded"},
]

_DEMO_R1_DEVICE_EVENTS = [
    {"id": 5001, "device_id": 301, "severity": "high", "is_open": 1, "event_type": "packet_loss", "incident_type": "transport"},
    {"id": 5002, "device_id": 201, "severity": "medium", "is_open": 0, "event_type": "latency_spike", "incident_type": "congestion"},
    {"id": 5003, "device_id": 102, "severity": "low", "is_open": 1, "event_type": "client_reauth", "incident_type": "wireless"},
]

_DEMO_R1_DEVICE_DAILY_METRICS = [
    {"id": 7001, "device_id": 101, "metric_date": "2026-05-25", "uptime_pct": 99.97, "latency_ms": 10.8, "packet_loss_pct": 0.11, "throughput_mbps": 422.5, "incidents": 0},
    {"id": 7002, "device_id": 102, "metric_date": "2026-05-25", "uptime_pct": 99.92, "latency_ms": 12.1, "packet_loss_pct": 0.16, "throughput_mbps": 398.3, "incidents": 1},
    {"id": 7003, "device_id": 201, "metric_date": "2026-05-25", "uptime_pct": 99.88, "latency_ms": 14.4, "packet_loss_pct": 0.22, "throughput_mbps": 361.7, "incidents": 1},
    {"id": 7004, "device_id": 301, "metric_date": "2026-05-25", "uptime_pct": 98.75, "latency_ms": 21.6, "packet_loss_pct": 1.05, "throughput_mbps": 242.9, "incidents": 3},
    {"id": 7005, "device_id": 101, "metric_date": "2026-05-26", "uptime_pct": 99.98, "latency_ms": 10.2, "packet_loss_pct": 0.08, "throughput_mbps": 436.1, "incidents": 0},
    {"id": 7006, "device_id": 102, "metric_date": "2026-05-26", "uptime_pct": 99.90, "latency_ms": 12.7, "packet_loss_pct": 0.19, "throughput_mbps": 405.2, "incidents": 1},
    {"id": 7007, "device_id": 201, "metric_date": "2026-05-26", "uptime_pct": 99.84, "latency_ms": 15.2, "packet_loss_pct": 0.27, "throughput_mbps": 352.8, "incidents": 1},
    {"id": 7008, "device_id": 301, "metric_date": "2026-05-26", "uptime_pct": 98.58, "latency_ms": 23.4, "packet_loss_pct": 1.22, "throughput_mbps": 231.4, "incidents": 4},
]

# ─── Pre-computed analytics ───────────────────────────────────────────

_TOTAL_PROPERTIES = len(_DEMO_PROPERTIES)
_TOTAL_UNITS = sum(p["total_units"] for p in _DEMO_PROPERTIES)
_OCCUPIED_UNITS = sum(p["units_occupied"] for p in _DEMO_PROPERTIES)
_TOTAL_NOI = sum(p["noi"] for p in _DEMO_PROPERTIES)
_AVG_CAP_RATE = round(sum(p["cap_rate"] for p in _DEMO_PROPERTIES) / _TOTAL_PROPERTIES, 1) if _TOTAL_PROPERTIES else 0
_AVG_RENT = round(sum(p["average_rent"] for p in _DEMO_PROPERTIES) / _TOTAL_PROPERTIES, 2) if _TOTAL_PROPERTIES else 0
_TOTAL_VALUE = sum(p["estimated_value"] for p in _DEMO_PROPERTIES)
_ACTIVE_DEALS_VALUE = sum(d["offer_price"] for d in _DEMO_DEALS if d["status"] == "Active")
_ACTIVE_DEALS_COUNT = len([d for d in _DEMO_DEALS if d["status"] == "Active"])
_CLOSED_VALUE = sum(d["offer_price"] for d in _DEMO_DEALS if d["status"] == "Closed")
_CLOSED_COUNT = len([d for d in _DEMO_DEALS if d["status"] == "Closed"])
_LOST_VALUE = sum(d["offer_price"] for d in _DEMO_DEALS if d["status"] == "Lost")
_TOTAL_COMMISSION = sum(d["commission_total"] for d in _DEMO_DEALS if d["status"] in ("Active", "Closed"))


class QueryRequest(BaseModel):
    query: str


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-sql", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "sql"}


def _keyword_match(q: str, words: list[str]) -> bool:
    return any(w in q for w in words)


def _demo_response(payload: QueryRequest) -> dict[str, Any]:
    """Return rich multifamily demo data when DAB is unavailable."""
    q = payload.query.lower()

    fetch_properties = _keyword_match(q, [
        "property", "properties", "building", "asset", "portfolio",
        "unit", "units", "occupy", "vacancy", "vacant", "rent", "noi",
        "cap rate", "value", "valuation", "sqft", "acre",
        "memphis", "germantown", "east memphis", "downtown",
        "overview", "all", "list", "show", "portfolio"
    ])
    fetch_contacts = _keyword_match(q, [
        "contact", "owner", "broker", "investor", "lender",
        "manager", "vendor", "agent", "person", "who",
        "represent", "company", "firm", "foster", "thornton"
    ])
    fetch_deals = _keyword_match(q, [
        "deal", "pipeline", "loi", "due diligence", "underwriting",
        "closing", "offer", "commission", "stage", "buyer",
        "seller", "acquisition", "disposition", "transaction",
        "sale", "sell", "buy", "trade", "contract"
    ])
    fetch_activities = _keyword_match(q, [
        "activity", "activities", "tour", "showing", "inspection",
        "appraisal", "meeting", "call", "follow", "upcoming",
        "schedule", "calendar", "task", "open item"
    ])
    fetch_metrics = _keyword_match(q, [
        "total", "sum", "average", "how many", "count", "pipeline",
        "kpi", "metric", "portfolio", "performance", "summary",
        "aggregate", "breakdown", "report"
    ])
    fetch_r1 = _keyword_match(q, [
        "r1", "ruckus", "wireless", "wifi", "network", "access point",
        "device event", "packet loss", "latency", "throughput", "incident"
    ])

    # Default: return everything if nothing specific matched
    if not any([fetch_properties, fetch_contacts, fetch_deals, fetch_activities, fetch_metrics, fetch_r1]):
        fetch_properties = True
        fetch_deals = True
        fetch_metrics = True

    results: dict[str, Any] = {
        "service": "sql",
        "mode": "demo",
        "query": payload.query,
        "summary": "Demo mode: returning multifamily & brokerage database",
    }

    # Filter properties by status or city
    props = _DEMO_PROPERTIES
    if fetch_properties:
        if _keyword_match(q, ["under contract", "pending"]):
            props = [p for p in props if p["status"] == "Under Contract"]
        elif _keyword_match(q, ["sold", "closed"]):
            props = [p for p in props if p["status"] == "Sold"]
        elif _keyword_match(q, ["germantown"]):
            props = [p for p in props if p["city"] == "Germantown"]
        elif _keyword_match(q, ["downtown"]):
            props = [p for p in props if "downtown" in (p.get("notes") or "").lower() or p["city"] == "Memphis" and p["zip"] and p["zip"].startswith("38103")]
        elif _keyword_match(q, ["east memphis"]):
            props = [p for p in props if p["city"] == "Memphis" and p["zip"] and p["zip"].startswith("3811")]

        if _keyword_match(q, ["active"]):
            props = [p for p in props if p["status"] == "Active"]

        results["properties"] = props
        results["properties_summary"] = f"Found {len(props)} properties"

        # Property-level metrics
        occupied = sum(p["units_occupied"] for p in props)
        total = sum(p["total_units"] for p in props)
        results["property_metrics"] = {
            "total_properties": len(props),
            "total_units": total,
            "occupied_units": occupied,
            "vacant_units": total - occupied,
            "occupancy_rate": round(occupied / total * 100, 1) if total else 0,
            "average_rent": round(sum(p["average_rent"] for p in props) / len(props), 2) if props else 0,
        }

    if fetch_contacts:
        results["contacts"] = _DEMO_CONTACTS
        results["contacts_summary"] = f"Found {len(_DEMO_CONTACTS)} contacts"

    if fetch_deals:
        # Filter by stage if mentioned
        deals = _DEMO_DEALS
        for stage in ("LOI", "Underwriting", "Due Diligence", "Closing", "Closed", "Lost"):
            if stage.lower() in q:
                deals = [d for d in deals if d["stage"] == stage]
                break
        # Filter by status
        if _keyword_match(q, ["active", "open", "pending"]):
            deals = [d for d in deals if d["status"] == "Active"]
        elif _keyword_match(q, ["closed", "won"]):
            deals = [d for d in deals if d["status"] == "Closed"]

        results["deals"] = deals
        results["deals_summary"] = f"Found {len(deals)} deal(s)"

    if fetch_activities:
        activities = _DEMO_ACTIVITIES
        if _keyword_match(q, ["open", "pending", "upcoming"]):
            activities = [a for a in activities if a["status"] == "Open"]
        elif _keyword_match(q, ["completed", "done"]):
            activities = [a for a in activities if a["status"] == "Completed"]
        results["activities"] = activities
        results["activities_summary"] = f"Found {len(activities)} activities"

    if fetch_metrics or (fetch_deals and _keyword_match(q, ["pipeline", "total", "value", "summary"])):
        results["metrics"] = {
            "portfolio": {
                "total_properties": _TOTAL_PROPERTIES,
                "total_units": _TOTAL_UNITS,
                "occupied_units": _OCCUPIED_UNITS,
                "vacant_units": _TOTAL_UNITS - _OCCUPIED_UNITS,
                "occupancy_rate": round(_OCCUPIED_UNITS / _TOTAL_UNITS * 100, 1),
                "average_rent": _AVG_RENT,
                "total_noi": _TOTAL_NOI,
                "average_cap_rate": _AVG_CAP_RATE,
                "total_portfolio_value": _TOTAL_VALUE,
            },
            "pipeline": {
                "active_deals": _ACTIVE_DEALS_COUNT,
                "active_deals_value": _ACTIVE_DEALS_VALUE,
                "closed_deals": _CLOSED_COUNT,
                "closed_deals_value": _CLOSED_VALUE,
                "lost_deals_value": _LOST_VALUE,
                "total_commission_pipeline": _TOTAL_COMMISSION,
                "avg_deal_size": round(_ACTIVE_DEALS_VALUE / _ACTIVE_DEALS_COUNT, 2) if _ACTIVE_DEALS_COUNT else 0,
            },
            "by_stage": {
                stage: {
                    "count": len([d for d in _DEMO_DEALS if d["stage"] == stage]),
                    "value": round(sum(d["offer_price"] for d in _DEMO_DEALS if d["stage"] == stage), 2),
                }
                for stage in ["LOI", "Underwriting", "Due Diligence", "Closing", "Closed", "Lost"]
            },
        }
        results["metrics_summary"] = (
            f"Portfolio: {_TOTAL_PROPERTIES} properties, {_TOTAL_UNITS} units, "
            f"{round(_OCCUPIED_UNITS / _TOTAL_UNITS * 100, 1)}% occupied. "
            f"Pipeline: ${_ACTIVE_DEALS_VALUE:,.0f} across {_ACTIVE_DEALS_COUNT} active deals. "
            f"Closed: ${_CLOSED_VALUE:,.0f} ({_CLOSED_COUNT} deals)."
        )

    if fetch_r1:
        results["r1_sites"] = _DEMO_R1_SITES
        results["r1_devices"] = _DEMO_R1_DEVICES
        results["r1_device_events"] = _DEMO_R1_DEVICE_EVENTS
        results["r1_device_daily_metrics"] = _DEMO_R1_DEVICE_DAILY_METRICS
        results["r1_summary"] = (
            "Demo network fallback data returned because SQL DAB endpoints are unavailable."
        )

    return results


@app.post("/mcp/query")
async def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    q = payload.query.lower()

    fetch_properties = _keyword_match(q, [
        "property", "properties", "building", "asset", "portfolio",
        "unit", "units", "occupy", "vacancy", "vacant", "rent", "noi",
        "cap rate", "value", "valuation", "sqft", "acre",
        "memphis", "germantown", "east memphis", "downtown",
        "overview", "all", "list", "show", "portfolio"
    ])
    fetch_contacts = _keyword_match(q, [
        "contact", "owner", "broker", "investor", "lender",
        "manager", "vendor", "agent", "person", "who",
        "represent", "company", "firm"
    ])
    fetch_deals = _keyword_match(q, [
        "deal", "pipeline", "loi", "due diligence", "underwriting",
        "closing", "offer", "commission", "stage", "buyer",
        "seller", "acquisition", "disposition", "transaction",
        "sale", "sell", "buy", "trade", "contract"
    ])
    fetch_activities = _keyword_match(q, [
        "activity", "activities", "tour", "showing", "inspection",
        "appraisal", "meeting", "call", "follow", "upcoming",
        "schedule", "calendar", "task", "open item"
    ])
    fetch_units = _keyword_match(q, [
        "unit", "unit mix", "floor plan", "vacant unit", "occupied unit"
    ])
    fetch_residents = _keyword_match(q, [
        "resident", "tenant", "renter", "household"
    ])
    fetch_leases = _keyword_match(q, [
        "lease", "renewal", "expiring", "move out", "move-in", "delinquent lease"
    ])
    fetch_work_orders = _keyword_match(q, [
        "work order", "maintenance", "service request", "ticket", "repair"
    ])
    fetch_charges = _keyword_match(q, [
        "charge", "ledger", "rent roll", "payment", "delinquent", "late fee", "collections"
    ])
    fetch_r1 = _keyword_match(q, [
        "r1", "ruckus", "wireless", "wifi", "network", "access point",
        "device event", "packet loss", "latency", "throughput", "incident"
    ])

    if not any([
        fetch_properties,
        fetch_contacts,
        fetch_deals,
        fetch_activities,
        fetch_units,
        fetch_residents,
        fetch_leases,
        fetch_work_orders,
        fetch_charges,
        fetch_r1,
    ]):
        fetch_properties = True
        fetch_deals = True

    results: dict[str, Any] = {"service": "sql", "query": payload.query}
    dab_available = False

    async with httpx.AsyncClient(timeout=15.0) as client:
        if fetch_properties:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Property")
                if resp.status_code == 200:
                    data = resp.json()
                    props = data.get("value", data)
                    results["properties"] = props
                    results["properties_summary"] = f"Found {len(props)} properties"
                    dab_available = True
            except Exception as exc:
                results["properties_error"] = str(exc)

        if fetch_contacts:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Contact")
                if resp.status_code == 200:
                    data = resp.json()
                    results["contacts"] = data.get("value", data)
                    results["contacts_summary"] = f"Found {len(results['contacts'])} contacts"
                    dab_available = True
            except Exception as exc:
                results["contacts_error"] = str(exc)

        if fetch_deals:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Deal")
                if resp.status_code == 200:
                    data = resp.json()
                    results["deals"] = data.get("value", data)
                    results["deals_summary"] = f"Found {len(results['deals'])} deals"
                    dab_available = True
            except Exception as exc:
                results["deals_error"] = str(exc)

        if fetch_activities:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Activity")
                if resp.status_code == 200:
                    data = resp.json()
                    results["activities"] = data.get("value", data)
                    results["activities_summary"] = f"Found {len(results['activities'])} activities"
                    dab_available = True
            except Exception as exc:
                results["activities_error"] = str(exc)

        if fetch_units:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Unit")
                if resp.status_code == 200:
                    data = resp.json()
                    results["units"] = data.get("value", data)
                    results["units_summary"] = f"Found {len(results['units'])} units"
                    dab_available = True
            except Exception as exc:
                results["units_error"] = str(exc)

        if fetch_residents:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Resident")
                if resp.status_code == 200:
                    data = resp.json()
                    results["residents"] = data.get("value", data)
                    results["residents_summary"] = f"Found {len(results['residents'])} residents"
                    dab_available = True
            except Exception as exc:
                results["residents_error"] = str(exc)

        if fetch_leases:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Lease")
                if resp.status_code == 200:
                    data = resp.json()
                    results["leases"] = data.get("value", data)
                    results["leases_summary"] = f"Found {len(results['leases'])} leases"
                    dab_available = True
            except Exception as exc:
                results["leases_error"] = str(exc)

        if fetch_work_orders:
            try:
                resp = await client.get(f"{DAB_BASE}/api/WorkOrder")
                if resp.status_code == 200:
                    data = resp.json()
                    results["work_orders"] = data.get("value", data)
                    results["work_orders_summary"] = f"Found {len(results['work_orders'])} work orders"
                    dab_available = True
            except Exception as exc:
                results["work_orders_error"] = str(exc)

        if fetch_charges:
            try:
                resp = await client.get(f"{DAB_BASE}/api/Charge")
                if resp.status_code == 200:
                    data = resp.json()
                    results["charges"] = data.get("value", data)
                    results["charges_summary"] = f"Found {len(results['charges'])} charges"
                    dab_available = True
            except Exception as exc:
                results["charges_error"] = str(exc)

        if fetch_r1:
            try:
                resp = await client.get(f"{DAB_BASE}/api/R1Site")
                if resp.status_code == 200:
                    data = resp.json()
                    results["r1_sites"] = data.get("value", data)
                    results["r1_sites_summary"] = f"Found {len(results['r1_sites'])} network sites"
                    dab_available = True
            except Exception as exc:
                results["r1_sites_error"] = str(exc)

            try:
                resp = await client.get(f"{DAB_BASE}/api/R1Device")
                if resp.status_code == 200:
                    data = resp.json()
                    results["r1_devices"] = data.get("value", data)
                    results["r1_devices_summary"] = f"Found {len(results['r1_devices'])} network devices"
                    dab_available = True
            except Exception as exc:
                results["r1_devices_error"] = str(exc)

            try:
                resp = await client.get(f"{DAB_BASE}/api/R1DeviceEvent")
                if resp.status_code == 200:
                    data = resp.json()
                    results["r1_device_events"] = data.get("value", data)
                    results["r1_device_events_summary"] = f"Found {len(results['r1_device_events'])} network device events"
                    dab_available = True
            except Exception as exc:
                results["r1_device_events_error"] = str(exc)

            try:
                resp = await client.get(f"{DAB_BASE}/api/R1DeviceDailyMetric")
                if resp.status_code == 200:
                    data = resp.json()
                    results["r1_device_daily_metrics"] = data.get("value", data)
                    results["r1_device_daily_metrics_summary"] = f"Found {len(results['r1_device_daily_metrics'])} network daily metrics"
                    dab_available = True
            except Exception as exc:
                results["r1_device_daily_metrics_error"] = str(exc)

    # Fall back to demo data if DAB is unavailable
    if not dab_available:
        return _demo_response(payload)

    return results

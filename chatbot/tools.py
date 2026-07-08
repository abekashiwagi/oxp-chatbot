"""OpenAI function-calling tool definitions mirroring the leasing-mcp tool surface.

All 38 tools follow the leasing-mcp naming standard (ADR-0002): snake_case
action verbs with 6-section descriptions and ToolAnnotations parity.
"""

TOOLS = [
    # ─── Property reads (17) ──────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_properties",
            "description": (
                "List communities in scope so you can identify the property the prospect is asking about.\n\n"
                "When to use:\n"
                "- Prospect asks 'what properties do you have?' or you need to resolve a property name to an id.\n\n"
                "Prerequisites:\n"
                "- property_ids (string or list of ints, required) — CSV or list of integer property ids.\n\n"
                "Returns: {data: [Property...]} — one row per property with name, rent ranges, bed/bath ranges, pet flags.\n\n"
                "Examples:\n"
                "- list_properties(property_ids='1062921')\n\n"
                "On error: {error: {field, expected, got, fix}} — read fix and apply."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_ids": {
                        "type": "string",
                        "description": "CSV of integer property ids, e.g. '1062921' or '1062921,1062922'"
                    }
                },
                "required": ["property_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property",
            "description": (
                "Load one community's headline profile so you can answer questions about that property.\n\n"
                "When to use:\n"
                "- Prospect asks 'tell me about this property' and you have the property_id.\n"
                "- Use list_properties first if you only have a name.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required) — integer id for the community.\n\n"
                "Returns: {data: Property} — name, descriptions, rent ranges, pet flags, availability.\n\n"
                "On error: {error: {field, expected, got, fix}}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer", "description": "Integer property id"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_addresses",
            "description": (
                "Get the physical and mailing addresses for a property.\n\n"
                "When to use:\n"
                "- Prospect asks 'where are you located?' or 'what's the address?'\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: [Address...]} — physical and mailing addresses."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_contact_details",
            "description": (
                "Get leasing office contact info (phone, email, website).\n\n"
                "When to use:\n"
                "- Prospect asks 'how do I reach you?' or 'what's your phone number?'\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: {phone, fax, email, website}}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_lease_terms",
            "description": (
                "Get available lease lengths and their descriptions.\n\n"
                "When to use:\n"
                "- Prospect asks 'what lease lengths do you offer?' or 'do you have short-term leases?'\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: [LeaseTerm...]} — term_months, name, description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_utilities",
            "description": (
                "Get utility responsibility breakdown (what's included vs. resident-paid).\n\n"
                "When to use:\n"
                "- Prospect asks 'what utilities are included?' or 'how much are utilities?'\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: [Utility...]} — utility name, responsibility (owner/resident), estimated cost."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_selling_points",
            "description": (
                "Get marketing highlights and selling points for the property.\n\n"
                "When to use:\n"
                "- Prospect asks 'what makes this place special?' or 'why should I live here?'\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: [SellingPoint...]} — title and description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_hours",
            "description": (
                "Get office hours and tour availability hours.\n\n"
                "When to use:\n"
                "- Prospect asks 'when are you open?' or 'what are your hours?'\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: {office_hours: [...], tour_hours: [...]}}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_policies",
            "description": (
                "Get pet, parking, lease, and move-in policies.\n\n"
                "When to use:\n"
                "- Prospect asks about pets, parking, lease terms, or move-in requirements.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: {pet_policy, parking_policy, lease_policy, move_in_policy}}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_specials",
            "description": (
                "Get current move-in specials and promotions.\n\n"
                "When to use:\n"
                "- Prospect asks 'any specials?' or 'do you have move-in deals?'\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: [Special...]} — name, description, dates, value."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_addons",
            "description": (
                "Get optional add-ons like reserved parking and storage units.\n\n"
                "When to use:\n"
                "- Prospect asks about parking options, storage, or extra services.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: [AddOn...]} — name, type, monthly cost, description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_floor_plans",
            "description": (
                "List all floor plan layouts with pricing and availability for a move-in date.\n\n"
                "When to use:\n"
                "- Prospect asks 'what floor plans do you have?' or 'show me your layouts.'\n"
                "- Need to resolve a floorplan name to an id for list_available_units.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n"
                "- move_in_date (str, required) — YYYY-MM-DD format. Ask the prospect if unknown.\n\n"
                "Returns: {data: [Floorplan...]} — name, beds/baths, sqft, rent range, units_available, media."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"},
                    "move_in_date": {"type": "string", "description": "YYYY-MM-DD format"}
                },
                "required": ["property_id", "move_in_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_floor_plan",
            "description": (
                "Get details for a single floor plan by id.\n\n"
                "When to use:\n"
                "- Prospect picked a specific layout and you need the full details.\n\n"
                "Prerequisites:\n"
                "- floorplan_id (int, required)\n\n"
                "Returns: {data: Floorplan} — single floor plan with all fields."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "floorplan_id": {"type": "integer"}
                },
                "required": ["floorplan_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_units",
            "description": (
                "Show rentable units for a property on the prospect's move-in date.\n\n"
                "When to use:\n"
                "- Prospect asks 'what's available?' or 'do you have a two-bedroom?'\n"
                "- Narrow by bedrooms, bathrooms, or floorplan after the prospect names preferences.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n"
                "- move_in_date (str, required) — YYYY-MM-DD. Ask prospect if unknown.\n"
                "- floorplan_id (int, optional) — filter to one layout.\n"
                "- number_of_bedrooms (number, optional) — 0 for studio, 1, 2, 3...\n"
                "- number_of_bathrooms (number, optional)\n\n"
                "Returns: {data: [Unit...]} — unit number, layout, sqft, rates by lease term."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"},
                    "move_in_date": {"type": "string"},
                    "floorplan_id": {"type": "integer"},
                    "number_of_bedrooms": {"type": "number"},
                    "number_of_bathrooms": {"type": "number"}
                },
                "required": ["property_id", "move_in_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_unit",
            "description": (
                "Get full details for a single unit by id.\n\n"
                "When to use:\n"
                "- Prospect wants details on a specific unit from list_available_units.\n\n"
                "Prerequisites:\n"
                "- unit_space_id (int, required)\n\n"
                "Returns: {data: Unit} — full unit details with rates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "unit_space_id": {"type": "integer"}
                },
                "required": ["unit_space_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_amenities",
            "description": (
                "Get community and unit amenities.\n\n"
                "When to use:\n"
                "- Prospect asks 'what amenities do you have?' or about specific amenities (pool, gym, etc.)\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: {community: [...], unit: [...]}} — amenity name, category, description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fee_catalog",
            "description": (
                "Get the fee schedule: application fees, pet fees, admin fees.\n\n"
                "When to use:\n"
                "- Prospect asks 'how much is the application fee?' or about move-in costs.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: {application_fees, pet_fees, admin_fees}}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    # ─── Availability reads (1) ───────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_unit_matrix",
            "description": (
                "Get a rent matrix showing pricing by move-in date and lease term for a specific unit.\n\n"
                "When to use:\n"
                "- Prospect wants to compare prices across different move-in dates or lease lengths.\n\n"
                "Prerequisites:\n"
                "- unit_space_id (int, required)\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: {unit_space_id, rent_matrix: [{move_in_date, rates: [...]}]}}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "unit_space_id": {"type": "integer"},
                    "property_id": {"type": "integer"}
                },
                "required": ["unit_space_id", "property_id"]
            }
        }
    },
    # ─── Tour lifecycle (8) ───────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "list_tour_types",
            "description": (
                "List all available tour types (in-person, self-guided, virtual).\n\n"
                "When to use:\n"
                "- Prospect asks 'what kinds of tours do you offer?'\n\n"
                "Returns: {data: [TourType...]} — name, display_name, description, duration."
            ),
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_available_tour_types",
            "description": (
                "Get tour types available at a specific property.\n\n"
                "When to use:\n"
                "- Before scheduling a tour, confirm which types this property supports.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n\n"
                "Returns: {data: [TourType...]}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"}
                },
                "required": ["property_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tour_schedule_time_slots",
            "description": (
                "Get available tour time slots for a date and tour type.\n\n"
                "When to use:\n"
                "- Prospect is ready to book and you need to show available times.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n"
                "- tour_date (str, required) — YYYY-MM-DD\n"
                "- tour_type (str, required) — 'tour', 'self_guided_tour', or 'virtual_tour'\n\n"
                "Returns: {data: [{date, tour_type, slots: [{start_time, end_time, available}]}]}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"},
                    "tour_date": {"type": "string"},
                    "tour_type": {"type": "string", "enum": ["tour", "self_guided_tour", "virtual_tour"]}
                },
                "required": ["property_id", "tour_date", "tour_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tours",
            "description": (
                "List all booked tours, optionally filtered by property or applicant.\n\n"
                "When to use:\n"
                "- Need to check if a prospect already has a tour scheduled.\n\n"
                "Returns: {data: [Tour...]}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"},
                    "applicant_id": {"type": "integer"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tour",
            "description": (
                "Get details for a single booked tour.\n\n"
                "When to use:\n"
                "- Prospect asks about their upcoming tour.\n\n"
                "Prerequisites:\n"
                "- tour_id (int, required)\n\n"
                "Returns: {data: Tour} — date, time, type, status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tour_id": {"type": "integer"}
                },
                "required": ["tour_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_tour",
            "description": (
                "Book a property tour at the date and time the prospect chose.\n\n"
                "When to use:\n"
                "- Prospect confirmed a tour type, date, and time slot.\n"
                "- MUST run capture_lead first to get application_id and applicant_id.\n\n"
                "Prerequisites:\n"
                "- application_id (int, required) — from capture_lead response\n"
                "- applicant_id (int, required) — from capture_lead response\n"
                "- property_id (int, required)\n"
                "- tour_type (str, required) — 'tour', 'self_guided_tour', or 'virtual_tour'\n"
                "- tour_date (str, required) — YYYY-MM-DD\n"
                "- time_slot (object, required) — {start_time: 'HH:MM', end_time: 'HH:MM'}\n\n"
                "Returns: confirmed tour with id, date, time, type, status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "integer"},
                    "applicant_id": {"type": "integer"},
                    "property_id": {"type": "integer"},
                    "tour_type": {"type": "string", "enum": ["tour", "self_guided_tour", "virtual_tour"]},
                    "tour_date": {"type": "string"},
                    "time_slot": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"}
                        },
                        "required": ["start_time", "end_time"]
                    }
                },
                "required": ["application_id", "applicant_id", "property_id", "tour_type", "tour_date", "time_slot"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_tour",
            "description": (
                "Change the date/time of an existing tour.\n\n"
                "When to use:\n"
                "- Prospect wants to move their tour to a different time.\n"
                "- Use this instead of cancel + re-book.\n\n"
                "Prerequisites:\n"
                "- tour_id (int, required)\n"
                "- new_tour_date (str, required) — YYYY-MM-DD\n"
                "- new_time_slot (object, required) — {start_time, end_time}\n\n"
                "Returns: updated tour confirmation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tour_id": {"type": "integer"},
                    "new_tour_date": {"type": "string"},
                    "new_time_slot": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"}
                        },
                        "required": ["start_time", "end_time"]
                    }
                },
                "required": ["tour_id", "new_tour_date", "new_time_slot"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_tour",
            "description": (
                "Cancel an existing tour.\n\n"
                "When to use:\n"
                "- Prospect explicitly asks to cancel, not reschedule.\n\n"
                "Prerequisites:\n"
                "- tour_id (int, required)\n\n"
                "Returns: cancellation confirmation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tour_id": {"type": "integer"}
                },
                "required": ["tour_id"]
            }
        }
    },
    # ─── Lead management (7) ──────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "capture_lead",
            "description": (
                "Create a guest card / lead in the CRM with the prospect's info.\n\n"
                "When to use:\n"
                "- You have the prospect's name and contact info and want to save them.\n"
                "- MUST run this before schedule_tour to get application_id and applicant_id.\n\n"
                "Prerequisites:\n"
                "- property_id (int, required)\n"
                "- first_name (str, required)\n"
                "- last_name (str, required)\n"
                "- email (str, optional)\n"
                "- phone (str, optional)\n"
                "- move_in_date (str, optional) — YYYY-MM-DD\n"
                "- desired_bedrooms (int, optional)\n\n"
                "Returns: {data: {id: application_id, primary_applicant: {id: applicant_id}}}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "move_in_date": {"type": "string"},
                    "desired_bedrooms": {"type": "integer"}
                },
                "required": ["property_id", "first_name", "last_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_leads",
            "description": (
                "Search for existing leads by email, phone, or name.\n\n"
                "When to use:\n"
                "- Check if a prospect already exists before creating a new lead.\n\n"
                "Returns: {data: [Lead...]}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_id": {"type": "integer"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lead",
            "description": (
                "Get details for a single lead / guest card.\n\n"
                "Prerequisites:\n"
                "- application_id (int, required)\n\n"
                "Returns: {data: Lead} — prospect info, status, activities."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "integer"}
                },
                "required": ["application_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_lead_activities",
            "description": (
                "Get activity history for a lead (emails, tours, notes).\n\n"
                "Prerequisites:\n"
                "- application_id (int, required)\n\n"
                "Returns: {data: [Activity...]} — type, timestamp, description."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "integer"}
                },
                "required": ["application_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_applicant",
            "description": (
                "Check if an applicant already exists by email or phone.\n\n"
                "When to use:\n"
                "- Before capture_lead, check for duplicates.\n\n"
                "Returns: {data: [Applicant...]} — existing applicant records."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "phone": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_applicant",
            "description": (
                "Update an existing applicant's information.\n\n"
                "Prerequisites:\n"
                "- applicant_id (int, required)\n"
                "- Fields to update: first_name, last_name, email, phone\n\n"
                "Returns: updated applicant record."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "applicant_id": {"type": "integer"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"}
                },
                "required": ["applicant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_guest_card",
            "description": (
                "Update an existing guest card / lead.\n\n"
                "Prerequisites:\n"
                "- application_id (int, required)\n"
                "- Fields to update: move_in_date, desired_bedrooms, source, notes\n\n"
                "Returns: updated guest card."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application_id": {"type": "integer"},
                    "move_in_date": {"type": "string"},
                    "desired_bedrooms": {"type": "integer"},
                    "source": {"type": "string"},
                    "notes": {"type": "string"}
                },
                "required": ["application_id"]
            }
        }
    },
    # ─── Platform (5) ─────────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "search_tools",
            "description": "Search the tool registry by keyword. Returns matching tool names and descriptions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ping",
            "description": "Liveness check. Returns {ok: true}.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_auth_token_demo",
            "description": "Auth client smoke test. Returns a redacted token for diagnostics.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "echo_request_headers",
            "description": "Echo inbound request headers with credentials redacted. For diagnostics.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List available agent skills. Legacy discovery tool.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
]

from app import app, db, ServiceUser, Volunteer, Admin, get_coordinates
from werkzeug.security import generate_password_hash


def populate_database():
    with app.app_context():
        print("Populating database with test data...")

        # Check if already populated
        if ServiceUser.query.count() > 0 or Volunteer.query.count() > 0:
            print("Database already has data!")
            response = input("Do you want to clear and repopulate? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled.")
                return

            # Clear existing data
            ServiceUser.query.delete()
            Volunteer.query.delete()
            db.session.commit()
            print("Cleared existing data.")

        # Same password for all: Admin123!
        password_hash = generate_password_hash('Admin123!')

        # ========== CREATE 25 SERVICE USERS (5 per city) ==========

        service_users = [
            # === BIRMINGHAM (5) ===
            {'name': 'Margaret Thompson', 'email': 'margaret.thompson@email.com', 'phone': '0121 496 0001', 'address': '12 Oak Lane, Edgbaston', 'postcode': 'B15 2TT', 'conditions': 'Elderly, living alone, Hoarding disorder', 'emergency_contact': '0121 496 1001'},
            {'name': 'George Williams', 'email': 'george.williams@email.com', 'phone': '0121 496 0002', 'address': '45 High Street, Harborne', 'postcode': 'B17 0DN', 'conditions': 'Limited mobility, Chronic illness / chronic pain', 'emergency_contact': '0121 496 1002'},
            {'name': 'Dorothy Evans', 'email': 'dorothy.evans@email.com', 'phone': '0121 496 0003', 'address': '78 Stratford Road, Sparkhill', 'postcode': 'B11 1AR', 'conditions': 'Hoarding disorder, Bereavement', 'emergency_contact': '0121 496 1003'},
            {'name': 'Arthur Brown', 'email': 'arthur.brown@email.com', 'phone': '0121 496 0004', 'address': '23 Hagley Road, Edgbaston', 'postcode': 'B16 8EB', 'conditions': 'Visual impairment', 'emergency_contact': '0121 496 1004'},
            {'name': 'Elizabeth Davies', 'email': 'elizabeth.davies@email.com', 'phone': '0121 496 0005', 'address': '56 Soho Road, Handsworth', 'postcode': 'B18 5LB', 'conditions': 'Physical disability, Elderly, living alone', 'emergency_contact': '0121 496 1005'},
            # === LONDON (5) ===
            {'name': 'Susan Harris', 'email': 'susan.harris@email.com', 'phone': '020 7946 0001', 'address': '73 Westminster Bridge Road, Lambeth', 'postcode': 'SE1 7PB', 'conditions': 'Limited mobility, Chronic illness / chronic pain', 'emergency_contact': '020 7946 1001'},
            {'name': 'Richard Robinson', 'email': 'richard.robinson@email.com', 'phone': '020 7946 0002', 'address': '59 Camden High Street, Camden', 'postcode': 'NW1 7JL', 'conditions': 'Mental health condition, Hoarding disorder', 'emergency_contact': '020 7946 1002'},
            {'name': 'Patricia Moore', 'email': 'patricia.moore@email.com', 'phone': '020 7946 0003', 'address': '14 Brixton Road, Brixton', 'postcode': 'SW9 6BU', 'conditions': 'Hoarding disorder, Mental health condition', 'emergency_contact': '020 7946 1003'},
            {'name': 'James Wilson', 'email': 'james.wilson@email.com', 'phone': '020 7946 0004', 'address': '88 Holloway Road, Islington', 'postcode': 'N7 8JG', 'conditions': 'Elderly, living alone', 'emergency_contact': '020 7946 1004'},
            {'name': 'Helen Clark', 'email': 'helen.clark@email.com', 'phone': '020 7946 0005', 'address': '31 Peckham High Street, Peckham', 'postcode': 'SE15 5EB', 'conditions': 'Physical disability, Financial hardship / low income', 'emergency_contact': '020 7946 1005'},
            # === EDINBURGH (5) ===
            {'name': 'Linda Young', 'email': 'linda.young@email.com', 'phone': '0131 225 0001', 'address': '64 Princes Street, New Town', 'postcode': 'EH2 2DG', 'conditions': 'Mental health condition, Financial hardship / low income', 'emergency_contact': '0131 225 1001'},
            {'name': 'Robert King', 'email': 'robert.king@email.com', 'phone': '0131 225 0002', 'address': '37 Leith Walk, Leith', 'postcode': 'EH6 5AH', 'conditions': 'Recovering from surgery or illness, Bereavement', 'emergency_contact': '0131 225 1002'},
            {'name': 'Fiona MacLeod', 'email': 'fiona.macleod@email.com', 'phone': '0131 225 0003', 'address': '22 Dalry Road, Dalry', 'postcode': 'EH11 2AQ', 'conditions': 'Limited mobility, Chronic illness / chronic pain', 'emergency_contact': '0131 225 1003'},
            {'name': 'Angus Stewart', 'email': 'angus.stewart@email.com', 'phone': '0131 225 0004', 'address': '15 Gorgie Road, Gorgie', 'postcode': 'EH11 2LA', 'conditions': 'Learning disability, Hoarding disorder', 'emergency_contact': '0131 225 1004'},
            {'name': 'Morag Campbell', 'email': 'morag.campbell@email.com', 'phone': '0131 225 0005', 'address': '8 Morningside Road, Morningside', 'postcode': 'EH10 4BZ', 'conditions': 'Elderly, living alone, Hoarding disorder', 'emergency_contact': '0131 225 1005'},
            # === BRISTOL (5) ===
            {'name': 'Jennifer Hall', 'email': 'jennifer.hall@email.com', 'phone': '0117 903 0001', 'address': '19 Park Street, Clifton', 'postcode': 'BS1 5PB', 'conditions': 'Dementia / cognitive decline, Elderly, living alone', 'emergency_contact': '0117 903 1001'},
            {'name': 'Michael Allen', 'email': 'michael.allen@email.com', 'phone': '0117 903 0002', 'address': '52 Gloucester Road, Bishopston', 'postcode': 'BS7 8BN', 'conditions': 'Limited mobility, Elderly, living alone', 'emergency_contact': '0117 903 1002'},
            {'name': 'Sarah Price', 'email': 'sarah.price@email.com', 'phone': '0117 903 0003', 'address': '6 Bedminster Parade, Bedminster', 'postcode': 'BS3 4HL', 'conditions': 'Limited mobility, Chronic illness / chronic pain', 'emergency_contact': '0117 903 1003'},
            {'name': 'Andrew Morris', 'email': 'andrew.morris@email.com', 'phone': '0117 903 0004', 'address': '41 Whiteladies Road, Clifton', 'postcode': 'BS8 2NT', 'conditions': 'Bereavement, Carer / caregiver burden', 'emergency_contact': '0117 903 1004'},
            {'name': 'Emma Baker', 'email': 'emma.baker@email.com', 'phone': '0117 903 0005', 'address': '29 Stapleton Road, Easton', 'postcode': 'BS5 0QQ', 'conditions': 'Hoarding disorder, Mental health condition', 'emergency_contact': '0117 903 1005'},
            # === SWANSEA (5) ===
            {'name': 'Gareth Jones', 'email': 'gareth.jones@email.com', 'phone': '01792 480 001', 'address': '18 High Street, Swansea', 'postcode': 'SA1 1LE', 'conditions': 'Learning disability, Financial hardship / low income', 'emergency_contact': '01792 480 101'},
            {'name': 'Rhiannon Davies', 'email': 'rhiannon.davies@email.com', 'phone': '01792 480 002', 'address': '45 Mansel Street, City Centre', 'postcode': 'SA1 5TY', 'conditions': 'Limited mobility, Chronic illness / chronic pain', 'emergency_contact': '01792 480 102'},
            {'name': 'Huw Thomas', 'email': 'huw.thomas@email.com', 'phone': '01792 480 003', 'address': '7 Bryn Road, Brynmill', 'postcode': 'SA2 0AT', 'conditions': 'Physical disability, Elderly, living alone', 'emergency_contact': '01792 480 103'},
            {'name': 'Cerys Williams', 'email': 'cerys.williams@email.com', 'phone': '01792 480 004', 'address': '33 Gower Road, Sketty', 'postcode': 'SA2 9BX', 'conditions': 'Chronic illness / chronic pain, Hoarding disorder', 'emergency_contact': '01792 480 104'},
            {'name': 'Dylan Morgan', 'email': 'dylan.morgan@email.com', 'phone': '01792 480 005', 'address': '12 Neath Road, Hafod', 'postcode': 'SA1 2HW', 'conditions': 'Dementia / cognitive decline, Carer / caregiver burden', 'emergency_contact': '01792 480 105'}
        ]

        for user_data in service_users:
            coords = get_coordinates(user_data['postcode'])
            latitude = coords[0] if coords else None
            longitude = coords[1] if coords else None
            
            user = ServiceUser(
                name=user_data['name'],
                email=user_data['email'],
                password=password_hash,
                phone=user_data['phone'],
                address=user_data['address'],
                postcode=user_data['postcode'],
                latitude=latitude,
                longitude=longitude,
                conditions=user_data['conditions'],
                emergency_contact=user_data['emergency_contact']
            )
            db.session.add(user)

        print("✓ Added 25 Service Users (5 cities)")

        # ========== CREATE 25 VOLUNTEERS (5 per city) ==========
        # Each city has at least 1 Flexible volunteer + varied availability
        # Skills EXACTLY match dropdown options
        
        volunteers = [
            # === BIRMINGHAM (5) ===
            {
                'name': 'Alex Turner',
                'email': 'alex.turner@email.com',
                'phone': '0121 555 0001',
                'address': '10 Cherry Grove, Edgbaston',
                'postcode': 'B15 3ES',
                'skills': 'General cleaning,Laundry assistance,Garden tidying',
                'bio': 'Full-time volunteer coordinator - flexible schedule, here to help anytime!',
                'monday_slot': 'Flexible', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Flexible',
                'thursday_slot': 'Flexible', 'friday_slot': 'Flexible', 'saturday_slot': 'Flexible', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'Sam Roberts',
                'email': 'sam.roberts@email.com',
                'phone': '0121 555 0002',
                'address': '25 Maple Street, Harborne',
                'postcode': 'B17 0HW',
                'skills': 'General cleaning,Laundry assistance',
                'bio': 'Retired early and love helping out - available whenever you need me!',
                'monday_slot': 'Flexible', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Flexible',
                'thursday_slot': 'Flexible', 'friday_slot': 'Flexible', 'saturday_slot': 'Flexible', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'Emma Collins',
                'email': 'emma.collins@email.com',
                'phone': '0121 555 0003',
                'address': '48 Cedar Avenue, Sparkhill',
                'postcode': 'B11 1LJ',
                'skills': 'General cleaning,Decluttering & Hoarding support',
                'bio': 'Uni student. Love meeting new people and making a difference!',
                'monday_slot': 'Late Afternoon', 'tuesday_slot': 'Late Afternoon', 'wednesday_slot': 'Late Afternoon',
                'thursday_slot': 'Late Afternoon', 'friday_slot': 'Late Afternoon', 'saturday_slot': 'Morning', 'sunday_slot': 'Morning'
            },
            {
                'name': 'Priya Patel',
                'email': 'priya.patel@email.com',
                'phone': '0121 555 0004',
                'address': '31 Ladywood Road, Ladywood',
                'postcode': 'B16 9LL',
                'skills': 'Laundry assistance,Decluttering & Hoarding support',
                'bio': 'Professional cleaner by trade, volunteering on my days off to give back.',
                'monday_slot': 'Not Available', 'tuesday_slot': 'Morning', 'wednesday_slot': 'Not Available',
                'thursday_slot': 'Morning', 'friday_slot': 'Not Available', 'saturday_slot': 'Flexible', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'David Okafor',
                'email': 'david.okafor@email.com',
                'phone': '0121 555 0005',
                'address': '62 Winson Green Road',
                'postcode': 'B18 4HA',
                'skills': 'General cleaning,Garden tidying,Decluttering & Hoarding support',
                'bio': 'Community worker with experience in hoarding support.',
                'monday_slot': 'Morning', 'tuesday_slot': 'Morning', 'wednesday_slot': 'Afternoon',
                'thursday_slot': 'Afternoon', 'friday_slot': 'Morning', 'saturday_slot': 'Not Available', 'sunday_slot': 'Not Available'
            },
            # === LONDON (5) ===
            {
                'name': 'Olivia Chen',
                'email': 'olivia.chen@email.com',
                'phone': '020 7946 2001',
                'address': '15 Borough Road, Lambeth',
                'postcode': 'SE1 1JA',
                'skills': 'General cleaning,Laundry assistance,Garden tidying',
                'bio': 'Retired teacher, love keeping busy and helping the community.',
                'monday_slot': 'Flexible', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Flexible',
                'thursday_slot': 'Flexible', 'friday_slot': 'Flexible', 'saturday_slot': 'Morning', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Marcus Johnson',
                'email': 'marcus.johnson@email.com',
                'phone': '020 7946 2002',
                'address': '42 Chalk Farm Road, Camden',
                'postcode': 'NW1 8AJ',
                'skills': 'General cleaning,Garden tidying',
                'bio': 'Part-time actor, full-time community helper!',
                'monday_slot': 'Morning', 'tuesday_slot': 'Not Available', 'wednesday_slot': 'Morning',
                'thursday_slot': 'Not Available', 'friday_slot': 'Afternoon', 'saturday_slot': 'Flexible', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'Aisha Khan',
                'email': 'aisha.khan@email.com',
                'phone': '020 7946 2003',
                'address': '28 Coldharbour Lane, Brixton',
                'postcode': 'SW9 8PR',
                'skills': 'Decluttering & Hoarding support,Laundry assistance',
                'bio': 'Social worker with experience supporting vulnerable adults.',
                'monday_slot': 'Afternoon', 'tuesday_slot': 'Afternoon', 'wednesday_slot': 'Late Afternoon',
                'thursday_slot': 'Late Afternoon', 'friday_slot': 'Not Available', 'saturday_slot': 'Morning', 'sunday_slot': 'Morning'
            },
            {
                'name': 'Tom Fletcher',
                'email': 'tom.fletcher@email.com',
                'phone': '020 7946 2004',
                'address': '91 Seven Sisters Road, Holloway',
                'postcode': 'N7 6BL',
                'skills': 'General cleaning,Laundry assistance',
                'bio': 'University student volunteering between lectures.',
                'monday_slot': 'Late Afternoon', 'tuesday_slot': 'Late Afternoon', 'wednesday_slot': 'Not Available',
                'thursday_slot': 'Late Afternoon', 'friday_slot': 'Late Afternoon', 'saturday_slot': 'Flexible', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Grace Adeyemi',
                'email': 'grace.adeyemi@email.com',
                'phone': '020 7946 2005',
                'address': '55 Rye Lane, Peckham',
                'postcode': 'SE15 5EW',
                'skills': 'General cleaning,Decluttering & Hoarding support',
                'bio': 'Nurse on shift rotation - available on my days off.',
                'monday_slot': 'Not Available', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Not Available',
                'thursday_slot': 'Flexible', 'friday_slot': 'Not Available', 'saturday_slot': 'Not Available', 'sunday_slot': 'Flexible'
            },
            # === EDINBURGH (5) ===
            {
                'name': 'Eilidh MacKenzie',
                'email': 'eilidh.mackenzie@email.com',
                'phone': '0131 225 2001',
                'address': '18 George Street, New Town',
                'postcode': 'EH2 2PF',
                'skills': 'General cleaning,Laundry assistance,Decluttering & Hoarding support',
                'bio': 'Retired civil servant. Keeping Edinburgh tidy one home at a time!',
                'monday_slot': 'Flexible', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Flexible',
                'thursday_slot': 'Flexible', 'friday_slot': 'Flexible', 'saturday_slot': 'Morning', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Callum Fraser',
                'email': 'callum.fraser@email.com',
                'phone': '0131 225 2002',
                'address': '77 Easter Road, Leith',
                'postcode': 'EH6 8DG',
                'skills': 'General cleaning,Garden tidying',
                'bio': 'Landscape gardener offering help with indoor and outdoor spaces.',
                'monday_slot': 'Morning', 'tuesday_slot': 'Morning', 'wednesday_slot': 'Afternoon',
                'thursday_slot': 'Afternoon', 'friday_slot': 'Morning', 'saturday_slot': 'Not Available', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Isla Robertson',
                'email': 'isla.robertson@email.com',
                'phone': '0131 225 2003',
                'address': '5 Dalry Road, Dalry',
                'postcode': 'EH11 2BQ',
                'skills': 'Laundry assistance,General cleaning',
                'bio': 'Edinburgh University nursing student, happy to help!',
                'monday_slot': 'Late Afternoon', 'tuesday_slot': 'Not Available', 'wednesday_slot': 'Late Afternoon',
                'thursday_slot': 'Not Available', 'friday_slot': 'Late Afternoon', 'saturday_slot': 'Flexible', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'Hamish Scott',
                'email': 'hamish.scott@email.com',
                'phone': '0131 225 2004',
                'address': '34 Gorgie Road, Gorgie',
                'postcode': 'EH11 2NB',
                'skills': 'General cleaning,Decluttering & Hoarding support',
                'bio': 'Mental health support worker with hoarding intervention experience.',
                'monday_slot': 'Afternoon', 'tuesday_slot': 'Not Available', 'wednesday_slot': 'Afternoon',
                'thursday_slot': 'Morning', 'friday_slot': 'Not Available', 'saturday_slot': 'Morning', 'sunday_slot': 'Morning'
            },
            {
                'name': 'Sophie Murray',
                'email': 'sophie.murray@email.com',
                'phone': '0131 225 2005',
                'address': '12 Morningside Drive, Morningside',
                'postcode': 'EH10 5LZ',
                'skills': 'General cleaning,Garden tidying,Laundry assistance',
                'bio': 'Stay-at-home mum volunteering while kids are at school.',
                'monday_slot': 'Morning', 'tuesday_slot': 'Morning', 'wednesday_slot': 'Morning',
                'thursday_slot': 'Morning', 'friday_slot': 'Morning', 'saturday_slot': 'Not Available', 'sunday_slot': 'Not Available'
            },
            # === BRISTOL (5) ===
            {
                'name': 'Jake Harper',
                'email': 'jake.harper@email.com',
                'phone': '0117 903 2001',
                'address': '33 Park Row, City Centre',
                'postcode': 'BS1 5LJ',
                'skills': 'General cleaning,Garden tidying,Laundry assistance',
                'bio': 'Recently retired plumber, happy to help with anything!',
                'monday_slot': 'Flexible', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Flexible',
                'thursday_slot': 'Flexible', 'friday_slot': 'Flexible', 'saturday_slot': 'Flexible', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Chloe Bennett',
                'email': 'chloe.bennett@email.com',
                'phone': '0117 903 2002',
                'address': '17 Gloucester Road, Bishopston',
                'postcode': 'BS7 8AA',
                'skills': 'General cleaning,Laundry assistance',
                'bio': 'Social work student. Everyone deserves a clean, safe space!',
                'monday_slot': 'Not Available', 'tuesday_slot': 'Not Available', 'wednesday_slot': 'Late Afternoon',
                'thursday_slot': 'Late Afternoon', 'friday_slot': 'Late Afternoon', 'saturday_slot': 'Flexible', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'Ryan Edwards',
                'email': 'ryan.edwards@email.com',
                'phone': '0117 903 2003',
                'address': '8 North Street, Bedminster',
                'postcode': 'BS3 1HJ',
                'skills': 'General cleaning,Garden tidying,Decluttering & Hoarding support',
                'bio': 'Freelance designer with flexible hours, keen to give back.',
                'monday_slot': 'Morning', 'tuesday_slot': 'Afternoon', 'wednesday_slot': 'Morning',
                'thursday_slot': 'Not Available', 'friday_slot': 'Afternoon', 'saturday_slot': 'Not Available', 'sunday_slot': 'Morning'
            },
            {
                'name': 'Megan Taylor',
                'email': 'megan.taylor@email.com',
                'phone': '0117 903 2004',
                'address': '55 Whiteladies Road, Clifton',
                'postcode': 'BS8 2LY',
                'skills': 'Decluttering & Hoarding support,General cleaning',
                'bio': 'Occupational therapist volunteering to support independent living.',
                'monday_slot': 'Not Available', 'tuesday_slot': 'Morning', 'wednesday_slot': 'Not Available',
                'thursday_slot': 'Morning', 'friday_slot': 'Not Available', 'saturday_slot': 'Flexible', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Liam Watts',
                'email': 'liam.watts@email.com',
                'phone': '0117 903 2005',
                'address': '71 Stapleton Road, Easton',
                'postcode': 'BS5 0QX',
                'skills': 'General cleaning,Laundry assistance',
                'bio': 'UWE student looking to make a positive impact in Bristol.',
                'monday_slot': 'Late Afternoon', 'tuesday_slot': 'Late Afternoon', 'wednesday_slot': 'Not Available',
                'thursday_slot': 'Late Afternoon', 'friday_slot': 'Not Available', 'saturday_slot': 'Morning', 'sunday_slot': 'Flexible'
            },
            # === SWANSEA (5) ===
            {
                'name': 'Owain Griffiths',
                'email': 'owain.griffiths@email.com',
                'phone': '01792 480 201',
                'address': '25 Walter Road, Swansea',
                'postcode': 'SA1 5NN',
                'skills': 'General cleaning,Laundry assistance,Garden tidying',
                'bio': 'Retired teacher, always happy to lend a hand around the community.',
                'monday_slot': 'Flexible', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Flexible',
                'thursday_slot': 'Flexible', 'friday_slot': 'Flexible', 'saturday_slot': 'Morning', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Sian Evans',
                'email': 'sian.evans@email.com',
                'phone': '01792 480 202',
                'address': '8 St Helens Road, City Centre',
                'postcode': 'SA1 4AP',
                'skills': 'General cleaning,Laundry assistance',
                'bio': 'Swansea University student, experienced in home care support.',
                'monday_slot': 'Late Afternoon', 'tuesday_slot': 'Late Afternoon', 'wednesday_slot': 'Late Afternoon',
                'thursday_slot': 'Not Available', 'friday_slot': 'Late Afternoon', 'saturday_slot': 'Flexible', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'Iwan Rees',
                'email': 'iwan.rees@email.com',
                'phone': '01792 480 203',
                'address': '41 Bryn Road, Brynmill',
                'postcode': 'SA2 0AU',
                'skills': 'Garden tidying,Decluttering & Hoarding support',
                'bio': 'Charity worker with experience in vulnerable adult support.',
                'monday_slot': 'Morning', 'tuesday_slot': 'Afternoon', 'wednesday_slot': 'Morning',
                'thursday_slot': 'Afternoon', 'friday_slot': 'Morning', 'saturday_slot': 'Not Available', 'sunday_slot': 'Not Available'
            },
            {
                'name': 'Bethan Lloyd',
                'email': 'bethan.lloyd@email.com',
                'phone': '01792 480 204',
                'address': '63 Gower Road, Sketty',
                'postcode': 'SA2 9BT',
                'skills': 'General cleaning,Decluttering & Hoarding support',
                'bio': 'Part-time nurse, volunteering on my days off.',
                'monday_slot': 'Not Available', 'tuesday_slot': 'Flexible', 'wednesday_slot': 'Not Available',
                'thursday_slot': 'Flexible', 'friday_slot': 'Not Available', 'saturday_slot': 'Not Available', 'sunday_slot': 'Flexible'
            },
            {
                'name': 'Rhodri Price',
                'email': 'rhodri.price@email.com',
                'phone': '01792 480 205',
                'address': '19 Neath Road, Hafod',
                'postcode': 'SA1 2HN',
                'skills': 'General cleaning,Garden tidying,Laundry assistance',
                'bio': 'Handyman and community volunteer. Happy to tackle any cleaning job!',
                'monday_slot': 'Afternoon', 'tuesday_slot': 'Not Available', 'wednesday_slot': 'Afternoon',
                'thursday_slot': 'Morning', 'friday_slot': 'Afternoon', 'saturday_slot': 'Flexible', 'sunday_slot': 'Morning'
            }
        ]

        for vol_data in volunteers:
            coords = get_coordinates(vol_data['postcode'])
            latitude = coords[0] if coords else None
            longitude = coords[1] if coords else None
            
            volunteer = Volunteer(
                name=vol_data['name'],
                email=vol_data['email'],
                password=password_hash,
                phone=vol_data['phone'],
                address=vol_data['address'],
                postcode=vol_data['postcode'],
                latitude=latitude,
                longitude=longitude,
                skills=vol_data['skills'],
                bio=vol_data['bio'],
                monday_slot=vol_data['monday_slot'],
                tuesday_slot=vol_data['tuesday_slot'],
                wednesday_slot=vol_data['wednesday_slot'],
                thursday_slot=vol_data['thursday_slot'],
                friday_slot=vol_data['friday_slot'],
                saturday_slot=vol_data['saturday_slot'],
                sunday_slot=vol_data['sunday_slot']
            )
            db.session.add(volunteer)

        print("✓ Added 25 Volunteers (5 cities)")

        db.session.commit()

        print(f"\n25 users, 25 volunteers across 5 UK cities")
        print("Cities: Birmingham, London, Edinburgh, Bristol, Swansea")
        print("Password for all accounts: Admin123!")


if __name__ == '__main__':
    populate_database()

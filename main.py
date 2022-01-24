import db
from hashlib import sha512
authorised_user = None
user_type = None

# helper functions
# print enumerated options from list
def print_options(options):
    for i, option in enumerate(options):
        print(i+1,". ",options[i], sep="")
    print("-"*24)

# take user input in a range, re-take input if incorrect
def userinput_range(start, end):
    choice = start-1
    while choice not in range(start, end+1):
        choice = int(input(f"Enter choice({start}-{end}): "))
        if choice not in range(start, end+1): print("Choice not in valid range")
    return choice

# perform the index-th function in the list with the index-th parameter list
def perform_action(index, actions, paramlists=None):
    if not paramlists: paramlists=[()]*len(actions)
    return actions[index](*paramlists[index])

# combine prev 3 helpers to show user options, take input, and perform the action
def userinput(options, actions, paramlists=None):
    assert len(options) == len(actions)
    print_options(options)
    choice = userinput_range(1, len(options))
    return perform_action(choice-1, actions, paramlists)
    

# salt password with username and return hashed result
def hashpwd(username, password):
    return sha512(bytes(username + password, 'utf-8')).hexdigest()

# helper function to return status msg of a status code
def statuscode(status):
    return {
        "OTW" : "On The Way",
        "DEL" : "Delivered",
        "PRC" : "Processing",
        "RET" : "Returned",
        "DAM" : "Damaged",
        "CAN" : "Cancelled",
        }[status]

def inputstring(value):
    inp = ""
    while inp == "":
        inp = input(f"Enter {value}: ")
        if inp == "": print(f"{value} cannot be empty")
    return inp


# signup actions
def xsignup(tablename):
    query = f"select username from {tablename} where username = ?"
    username = None
    while not username:
        username = input("Enter username (max 32 characters): ")
        user = db.execute_read(connection, query, (username,))
        if user:
            print("Username is taken, Please choose some other username")
            username = None
    password = input("Enter password: ")
    hashedpw = hashpwd(username, password)
    name = input("Enter Name: ")
    phone = input("Enter phone number: ")
    query = f"insert into {tablename} values(?, ?, ?, ?);"
    if not db.execute(connection, query, (username,hashedpw,name,phone)):
        print("Error while creating user")
    else:
        print("Sign up successful")
    mainmenu()

def signup_cust():
    xsignup('customer')

def signup_agent():
    xsignup('agent')

def signup():
    options = ["Sign Up as a Customer", "Sign up as an Delivery Agent", "Exit"]
    actions = [signup_cust, signup_agent, exit]
    userinput(options, actions)
    

# customer helper actions
def package_details_cust(package):
    orderid, deliveryid, status, rname, address, weight, _type, rate, typename, payment = package;
    print("Order UID:", orderid)
    print("Status:", status, f"({statuscode(status)})")
    print("Recipient Name:", rname)
    print("Recipient Address:", address)
    print("Weight:", weight,"gm")
    print("Item Type:", _type + " (" + typename+")")
    print("Rate: ", rate)
    print("Total Price: Rs.", rate * weight)
    print("Payment Method:", payment)
    print("-"*24)
    options = []
    actions = []
    paramlists = []
    if status == 'OTW': # customer can only mark status of package which is OTW as CAN
        options += ["Mark as Cancelled"]
        actions += [mark_del_status]
        paramlists += [(deliveryid, 'CAN')]
    options += ["Back", "Exit"]
    actions += [trackpack, exit]
    paramlists += [()]*2
    userinput(options, actions,paramlists)
    trackpack()

# customer actions
def trackpack():
    if user_type != 'customer' or not authorised_user:
        print("User should be customer")
        exit()
    query = """
    select 
        orders.id,
        delivery.id,
        delivery.status,
        delivery.recipientname,
        delivery.address, 
        item.weight, 
        item.type, 
        item_types.rate, 
        item_types.label, 
        orders.payment 
    from 
        delivery, 
        item, 
        item_types, 
        orders 
    where 
        orders.customer = ? and 
        orders.delivery = delivery.id and 
        delivery.item = item.id and 
        item.type = item_types.id;
    """
    packages = db.execute_read(connection, query, (authorised_user,))
    if len(packages) == 0:
        print("No packages to display")
        mainmenu()
        return
    if not packages:
        print("Error fetching packages")
        mainmenu()
        return
    print("#\tStatus\tDelivery Address\t\t\tWeight\tType\t\tPrice\tPayment Method") # print packages
    for index, package in enumerate(packages):
        orderid, deliveryid, status, rname, address, weight, _type, rate, typename, payment = package;
        print(index+1,status,address, f"{weight}gm", _type + " (" + typename+")", f"₹{weight * rate}" , payment,  sep="\t")
    print("Choose package to show more details")
    print("Enter 0 to go back")
    choice = userinput_range(0, len(packages))
    actions = [mainmenu] + [package_details_cust]*len(packages)
    paramlists = [()] + [(packages[choice-1],)]*len(packages)
    perform_action(choice, actions, paramlists)

def paycash():
    return "CASH"

def paycard():
    cardno = input("Enter card number: ")
    expmon = input("Enter expiry month: ")
    expyear = input("Enter expiry year: ")
    cvv = input("Enter CVV: ")
    print("Please wait for OTP to arrive and enter OTP")
    otp = input("Enter OTP: ")
    return "CARD#"+cardno


def payupi():
    print("Please make a payment of the above mentioned amount to UPI ID courier@oksbi")
    txnid = ""
    while txnid == "":
        txnid = input("Enter transaction ID after making payment: ")
        if txnid == "": print("Enter valid transaction ID")
    return "UPI#"+txnid
    
def findagent():
    query = "select agent, count(agent) from delivery where status='OTW' group by agent order by count(agent);"
    agentlist = db.execute_read(connection, query)
    agentdict = {agent[0]:agent[1] for agent in agentlist}
    query = "select username from agent"
    agentlist = db.execute_read(connection, query)
    for agent in agentlist:
        if agent[0] not in agentdict:
            agentdict[agent[0]] = 0
    minheap = list(dict(sorted(agentdict.items(),key=lambda i:i[1])))
    if not minheap:
        print("ERROR: No agent to assign to")
        return None
    return minheap[0]

def newcourier():
    print("Enter type of Item to be parcelled ")
    query = "select id, label from item_types;"
    itemtypes = db.execute_read(connection, query)
    if not itemtypes:
        print("Error fetching item types")
        exit()
    print_options(itemtypes)
    choice = userinput_range(1, len(itemtypes))
    itemtype = itemtypes[choice-1]
    query = "select rate from item_types where id = ?"
    rate = db.execute_read(connection, query, (itemtype[0],))[0][0]
    print(f"Rate of {itemtype} is ₹{rate}/gm")
    weight = 0.0
    while weight <= 0:
        weight = float(input("Enter weight of parcel(in gms): "))
        if weight <= 0: print("Weight need to be positive")
    recname = inputstring("Recipient Name")
    recaddress = inputstring("Recipient Address")

    print(f"Total price payable = ₹{rate}/gm * {weight}gm = ₹{rate*weight}")
    choice = input("Confirm? Y/N: ")
    if choice.strip().upper() != 'Y':
        mainmenu()
        return
        
    paymentoptions = ["CASH", "CARD", "UPI"]
    actions = [paycash, paycard, payupi]
    print("Enter payment method")
    paymentstring = userinput(paymentoptions, actions)

    added = False
    query = """insert into item(weight, type) values(?, ?);"""
    if db.execute(connection, query, (weight, itemtype[0])):
        query = """select last_insert_rowid();"""
        itemid = db.execute_read(connection, query)
        if itemid:
            itemid = itemid[0][0]
            agent = findagent()
            if agent:
                query = """insert into delivery(status, recipientname, address, agent, item) values('OTW', ?, ?, ?, ?);"""
                if db.execute(connection, query, (recname, recaddress, agent, int(itemid))):
                    query = """select last_insert_rowid();"""
                    delid = db.execute_read(connection, query)
                    if delid:
                        delid = delid[0][0]
                        query = """insert into orders(customer, delivery, payment) values(?, ?, ?);"""
                        if db.execute(connection, query, (authorised_user, int(delid), paymentstring)):
                            added = True
    
    if added: print("Order placed successfully")
    else: print("Unable to place order")
    mainmenu()

# agent helper actions
def mark_del_status(_id, status):
    query = "update delivery set status = ? where id = ?"
    if not db.execute(connection, query, (status, _id)):
        print("Error setting delivery status")
        return False
    else:
        print("Delivery Status Updated Successfully")
        return True

def package_details(package):
    _id, status, recipientname, address, agent, itemno = package;
    print("Delivery UID:", _id)
    print("Status:", status, f"({statuscode(status)})")
    print("Recipient Name:", recipientname)
    print("Delivery Address:", address)
    print("Item UID:", itemno)
    print("-"*24)
    options = []
    actions = []
    paramlists = []
    if status == 'OTW': # delivery partner can only mark status of package which is OTW with him
        options += ["Mark as Delivered", "Mark as Returned", "Mark as Damaged"]
        actions += [mark_del_status]*3
        paramlists += [(_id, 'DEL'), (_id, 'RET'), (_id, 'DAM')]
    options += ["Back", "Exit"]
    actions += [assignments, exit]
    paramlists += [()]*2
    userinput(options, actions,paramlists)
    assignments()
        
# agent actions
def assignments():
    if user_type != 'agent' or not authorised_user: # if not agent
        print("User should be agent")
        exit()
    query = "select * from delivery where agent = ?;" # get all the packages deliverable/delivered by this agent
    packages = db.execute_read(connection, query, (authorised_user,))
    if not packages:
        print("Error fetching packages")
        mainmenu()
        return
    print("#\tStatus\tRecipient Name\tAddress") # print packages
    for index, package in enumerate(packages):
        _id, status, recipientname, address, agent, itemno = package;
        print(index+1,status,recipientname,address, sep="\t")
    print("Choose package to show more details")
    print("Enter 0 to go back")
    choice = userinput_range(0, len(packages))
    actions = [mainmenu] + [package_details]*len(packages)
    paramlists = [()] + [(packages[choice-1],)]*len(packages)
    perform_action(choice, actions, paramlists)
        
# common actions
def update_name():
    name = input("Enter new name: ")
    query = f"update {user_type} set name = ? where username = ?"
    if not db.execute(connection, query,(name, authorised_user)):
        print("Error occured while updating name")
    else:
        print("Name Updated Successfully")
        mainmenu()

def update_phone():
    phone = input("Enter new phone number: ")
    query = f"update {user_type} set phone = ? where username = ?"
    if not db.execute(connection, query,(phone, authorised_user)):
        print("Error occured while updating phone number")
    else:
        print("Phone Number Updated Successfully")
        mainmenu()

def update_pass():
    passwd = input("Enter new password: ")
    passwd2 = input("Confirm password: ")
    if passwd != passwd2:
        print("Passwords dont match")
        exit()
    hashedpw = hashpwd(authorised_user, passwd)
    query = f"update {user_type} set passwordhash = ? where username = ?"
    if not db.execute(connection, query,(hashedpw, authorised_user)):
        print("Error occured while updating password")
    else:
        print("Password Changed Successfully")
        mainmenu()

def mydetails():
    username = authorised_user
    query = f"select * from {user_type} where username = ?;"
    user = db.execute_read(connection, query, (username,))
    if not user:
        print("Error occured while fetching agent details. Aborting")
        exit()
    user = user[0]
    print("Name:", user[2])
    print("username:", user[0])
    print("Phone Number:", user[3])

    options = ["Update Name", "Update Phone Number", "Change Password", "Back", "Exit"]
    actions = [update_name, update_phone, update_pass, mainmenu, exit]
    userinput(options, actions)

# login
def xlogin(tablename):
    global user_type, authorised_user
    username = input(f"Enter {tablename} username: ")
    password = input("Enter password: ")
    query = f"select username, passwordhash from {tablename} where username = ?;"
    user = db.execute_read(connection, query, (username,))
    if not user or user[0][1] != hashpwd(username, password):
        print("Invalid Username or Password")
        return False
    user_type = tablename
    authorised_user = username
    return True

def cuslogin():
    if(not xlogin('customer')):
        mainmenu()
        return
    options = ["Track Package", "Make New Courier", "My Details", "Exit"]
    actions = [trackpack, newcourier, mydetails, exit]
    userinput(options, actions)

def agentlogin():
    if(not xlogin('agent')):
        mainmenu()
        return
    options = ["My Assignments", "My Details", "Exit"]
    actions = [assignments, mydetails, exit]
    userinput(options, actions)

def login():
    options = ["Customer Login", "Agent Login", "Exit"]
    actions = [cuslogin, agentlogin, exit]
    userinput(options, actions)

# main menu
def mainmenu():
    if not authorised_user:
        options = ["Login", "New User (Sign up)", "Exit"]
        actions = [login, signup, exit]
        userinput(options,actions)
    elif user_type == 'agent':
        print("Logged in as: ", authorised_user, f"({user_type})")
        options = ["My Assignments", "My Details", "Exit"]
        actions = [assignments, mydetails, exit]
        userinput(options, actions)
    elif user_type == 'customer':
        print("Logged in as: ", authorised_user, f"({user_type})")
        options = ["Track Package", "Make New Courier", "My Details", "Exit"]
        actions = [trackpack, newcourier, mydetails, exit]
        userinput(options, actions)


if __name__ == '__main__':
    heading = "Courier Mailing System"
    print(len(heading)*"-","\n"+heading,"\n"+len(heading)*"-")
    connection = db.connect("database.db")
    if not connection:
        print("Unable to connect to database ('database.db')")
        print("Make sure to create the database and store it in root of project")
        print("A mock database is present as mock.db. Use it to get to know the schema")
        exit()
    mainmenu()
    
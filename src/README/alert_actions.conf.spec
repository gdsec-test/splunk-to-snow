
[create_service_now_ticket]
param.service_username = <string>
* Username of the Service-Now user to create the ticket with.
* Required.
* Set from the Set Up page for this app.

param.service_password = <string>
* Password of the Service-Now user to cerate the ticket with.
* Required.
* Set from the Set Up page for this app.

param.environment = <string>
* The service-now environment to send the ticket to.
* Required.
* Default = "dev"

param.table = <list>
* Service now table to create the ticket in.
* Required
* Default = "u_physical_security"

param.state = <string>
* The state of the ticket.
* Required.
* Default = "New"

param.ticket_urgency = <number>
* Urgency of the ticket.
* Required.
* Default = 3

param.ticket_impact = <number>
* Impact of the ticket.
* Required.
* Default = 3

param.ticket_title = <string>
* Title of the ticket.
* Required.
* Default = "New Splunk Alert"

param.ticket_event_time = [none | "now" | event_field]
* A ISO-8601 timestamp. To populate the Event Time field of the ticket.
* - none: Empty.
* - "now": Will set to the system time of the Splunk instance of when the alert was triggered.
* - event_field: A field from the event.
* Default = none

param.ticket_detect_time = <string>
* A ISO-8601 timestamp. To populate the Detect Time field of the ticket.
* - none: Empty.
* - "now": Will set to the system time of the Splunk instance of when the alert was triggered.
* - event_field: A field from the event.
* Default = none

param.ticket_assignment_group = <string>
* Service-Now Id of the assignment group of the ticket. Case-sensitive.
* Default = none

param.ticket_category = <string>
* Category of the ticket. Case-sensitive.
* Default = none

param.ticket_sub_category = <string>
* Sub-Category of the ticket.
* Default = none

param.ticket_summary = <string>
* Main body of the ticket. "Summary" or "Description" depending on the Service-Now table.
* Default = none

param.ticket_dsr = <string>
* Whether to check the DSR box in SNOW.
* Required.
* Default = "No"

param.ticket_detection_method = <string>
* Detection method field in SNOW
* Default = none

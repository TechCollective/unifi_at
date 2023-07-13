#!/usr/bin/env python
import requests
import json
import csv
import sys
import time
from datetime import datetime, timedelta
#from pyunifi.controller import Controller # TechCollective's feature branch
import pyunifi
import pyautotask
#from pyautotask.atsite import atSite
#config file within the same directory
import config

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import *
import dateutil.parser
import csv

# TODO Move this to the unifi_controllers database
c = pyunifi.controller.Controller(config.UnifiHost, config.UnifiUsername, config.UnifiPassword, config.UnifiPort, "v5")
# TODO Move this to the autotask_tenants database
at = pyautotask.atsite.atSite(config.atHost, config.atUsername, config.atPassword, config.atAPIInterationcode)

engine = create_engine('sqlite:///manifold.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# TODO We need to move this to a Databse cache.
tickets_entity_information_fields = at._api_read("Tickets/entityInformation/fields")['fields']


# TODO Sync Datto RMM - Sync description based on some criteria. last user

# TODO Need to figure out how to trigger a sync to subchannels when a change is made. Maybe add a  last modified field to companies. If last modified is greater than last_full_sync on subchannel, sync that company. Or something

# TODO Check Autotask contract. Unifi Site Description get assigned from Autotask "companyNumber - companyName". If they don't have a contract, they get the prefix name in UniFi with zz-$
def main():
    update_last_sync()
    # TODO Sync within Autotask. I'm not sure if rmmDeviceAuditHostname syncs back to referenceTitle, if not, we should. Maybe sync "rmmDeviceAuditDescription" to description
    # TODO Sync UniFi clients both ways. If a client is defined in UniFi make sure it has a CI in Autotask. All Autotask CI's should be created in UniFi.
    unifi_alerts_all()

    #get_autotask_tickets_entity_information()
    

def sync_channels(channel, db_obj, channel_sync_device=None):
    if channel.__class__.__name__ != "UniFi_Controllers": 
        link_unifi_company = session.query( Link_UniFi_Companies ).filter_by( companies_key=db_obj.company_key ).first()
        if link_unifi_company:
            unifi_site = session.query( UniFi_Sites ).filter_by( primary_key=link_unifi_company.unifi_sites_key ).first()
            c.site_id = unifi_site.name
            if db_obj.__class__.__name__ == "Devices":
                # TODO instead of for looping though all the site's clients, we should just sync them and for loop though link_unifi_client_devices
                unifi_clients = c.get_clients()
                for unifi_client in unifi_clients:
                    link_unifi_device = session.query( Link_UniFi_Devices ).filter_by( device_key=db_obj.primary_key ).first()
                    # if device is in link_unifi_device table, skip sync (thought set up to be able to allow a rename)
                    if not link_unifi_device:
                        for mac_raw in db_obj.macs:
                            mac = ((mac_raw.mac_addresses).strip())
                            if mac == unifi_client['mac']:
                                if db_obj.description: 
                                    unifi_name = db_obj.name + " - " + db_obj.description
                                else:
                                    unifi_name = db_obj.name
                                
                                # TODO We would have to modify set_client_alias, but we can send data to "notes" as well
                                if "name" in unifi_client:
                                    if unifi_name != unifi_client['name']:
                                        c.set_client_alias(mac,unifi_name)
                                else:
                                    c.set_client_alias(mac,unifi_name)
    if channel.__class__.__name__ != "Autotask_Tenants": 
        if db_obj.__class__.__name__ == "Devices":
            # pull device from autotask
            # check diffs
            print("Send device to Autotask")
            print(db_obj)
            sys.exit()
            params = {}
            params['referenceTitle'] = channel_sync_device.name
            params['serialNumber '] = channel_sync_device.serial
            # TODO add UDFs

            if db_obj.manufacturer == 'Ubiquiti':
                ci_category = session.query( Autotask_CI_Catagories ).filter_by( name="Unifi Controller Devices")
                params['configurationItemCategoryID '] = ci_category.id
                params['configurationItemType'] = ci_type.value
                ci_type = session.query( Autotask_CI_Types ).filter_by( label="Network Device")
                params['companyID'] = channel_sync_device.company_key
                #ci_product = session.query( Autotask_Products ).filter_by( )
                params['productID'] = 0
            else:
                print("Was not a UniFi device. Stopping")
                sys.exit()
            at.ci_push(params)

def update_last_sync():
    update_autotask_last_sync()
    update_unifi_last_sync()

def update_unifi_last_sync():
    print("Unifi Sync")
    tenant = session.query( UniFi_Controllers ).filter_by(host=config.UnifiHost).first()
    if tenant:
        # TODO currently set to 24 hours, but that should be configurable
        if (datetime.now() - tenant.last_full_sync).total_seconds() / 3600 > 24:
            _sync_unifi_sites(tenant)
            sync_unifi_devices()
            sync_unifi_clients()
    else:
        _sync_unifi_sites()
        sync_unifi_devices()
        sync_unifi_clients()

def get_unifi_alert_config(alert_key):
    # TODO need error checking here. Make sure the file is formated correctly
    reader = csv.DictReader(open('unifi_alerts_config.csv'))
    alerts_config = {}
    for row in reader:
        key = row.pop('Event')
        if key in alerts_config:
            pass
        alerts_config[key] = row
    alert_config = None
    for key in alerts_config:
        if key == alert_key:
            alert_config = alerts_config[key]
            break
    return alert_config

def unifi_site_down(unifi_site, ticket_params):
    unifi_alert_config = get_unifi_alert_config("CUSTOM_SITE_DOWN")

    ticket_params['title'] = unifi_alert_config['Ticket Title']
    ticket_params['issueType'] = get_autotask_tickets_field_value("issueType", unifi_alert_config['Issue type'])
    ticket_params['subIssueType'] = get_autotask_tickets_field_value("subIssueType", unifi_alert_config['Subissue type'])
    ticket_params['status'] = get_autotask_tickets_field_value("status", 'New')
    ticket_params['queueID'] = get_autotask_tickets_field_value("queueID", unifi_alert_config['Queue'])
    ticket_params['source'] = get_autotask_tickets_field_value("source", 'Monitoring Alert')
    ticket_params['description'] = "Gateway and all UniFi devices are off line"
    
    if 'id' in ticket_params:
        print(ticket_params)
        sys.exit()
    else:
        ticket_params['description'] += "\nUnifi Site is not assassoicated with an Autotask Company."
        ticket_params['description'] += "\nSite ID: " + unifi_site.name
        ticket_params['description'] += "\nSite Description: " + unifi_site.desc
        # TODO Move the filter to looking up the linked site controller. This will not work with mutiple unifi controllers
        unifi_controller_query = session.query( UniFi_Controllers ).filter_by(host=c.host ).first()
        ticket_params['description'] += "\nUniFi Controller: " + unifi_controller_query.host

def unifi_device_status():
    # TODO If on SLA contract, send ticket for all off line devices. If on UniFi contract, send ticket only for site down
    unifi_controller_query = session.query( UniFi_Controllers ).filter_by(host=c.host ).first()
    # TODO change sites_query to only look up for this controller
    sites_query = session.query(  UniFi_Sites )
    for site in sites_query:
        unifi_site_query = session.query( UniFi_Sites ).filter_by(name=site.name, controller_key=unifi_controller_query.primary_key ).first()
        link_unifi_site = session.query( Link_UniFi_Companies ).filter_by( unifi_sites_key=unifi_site_query.primary_key ).first()
        company_key = 0
        if hasattr(link_unifi_site, "primary_key"): 
            company_key = link_unifi_site.companies_key
            link_autotask_company = session.query( Link_Autotask_Companies ).filter_by( companies_key=company_key)
            c.site_id = site.name
            gateway_down = False
            devices_down = 0
            devices_total = 0
            unifi_devices = get_unifi_devices_basic()
            for unifi_device in unifi_devices:
                if unifi_device['adopted'] == True:
                    devices_total += 1
                    if unifi_device['state'] == 0:
                        devices_down += 1
                        if unifi_device['in_gateway_mode'] == True:
                            gateway_down = True
            if gateway_down == True and devices_total == devices_down:
                ticket_params = {}
                if hasattr(link_autotask_company, "primary_key"):
                    ticket_params['companyID'] = link_autotask_company.id
                unifi_site_down(site, ticket_params)
            else:
                pass
                # if sla and devices_down > 0:
                    #for device in devices:
                        #if device['adopted'] == True:
                            # If no 'Lost_Contact' ticket for device
                                # create 'Lost_Contact' ticket

def archive_unifi_alert(alert_id):
	params = {'_id': alert_id}
	return c._run_command('archive-alarm', params, mgr="evtmgr")

def check_autotask_existing_ticket(m_alert, event_config):
    print(event_config)
    filter_fields = ""

    if hasattr(m_alert, "at_id"):
        filter_fields = at.create_filter("eq", "configurationItemID", str(m_alert.device_from.at_id))
    if filter_fields == "":
        filter_fields = at.create_filter("eq", "subIssueType", get_autotask_tickets_field_value("subIssueType",event_config['Subissue type']))
    else:
        filter_fields = filter_fields + "," + at.create_filter("eq", "subIssueType", get_autotask_tickets_field_value("subIssueType",event_config['Subissue type']))
    filter_fields = filter_fields + "," + at.create_filter("eq", "companyID", str(m_alert.at_company_id))
    filter_fields = filter_fields + "," + at.create_filter("noteq", "status", get_autotask_tickets_field_value("status", 'Complete') )
    return at.create_query("tickets", filter_fields)

def create_unifi_alert_ticket(m_alert, alert_config):
    ticket_exsiting = check_autotask_existing_ticket(m_alert, alert_config)
    print(ticket_exsiting)
    #TODO maybe add an updated note
    if ticket_exsiting == []:
        print("         - Creating Ticket")
        print(alert_config['Subissue type'])
        params = {
                'title': alert_config['Ticket Title'],
                #'companyID': company['id'],
                'companyID': m_alert.at_company_id,
                'issueType': get_autotask_tickets_field_value("issueType", alert_config['Issue type']),
                'subIssueType': get_autotask_tickets_field_value("subIssueType", alert_config['Subissue type']),
                'status': get_autotask_tickets_field_value("status", 'New'),
                'queueID': get_autotask_tickets_field_value("queueID", alert_config['Queue']),
                'source' : get_autotask_tickets_field_value("source", 'Monitoring Alert'),
            }
        params['description'] = 'Message from the UniFi Controller is: ' + m_alert.alert_time.strftime("%Y-%m-%d, %H:%M") + " " + m_alert.message

        print(params)
        print("Create UniFi alert ticket")
        sys.exit()
    #     #if m_alert.device_from.at_id:
    #     if hasattr(m_alert, "at_id"):
    #         params['configurationItemID'] = m_alert.device_from.at_id

    #     if m_alert.unifi_alert_key == "EVT_GW_Lost_Contact":
    #         params['priority'] = get_tickets_field_value("priority", 'Critical')
    #     else:
    #         params['priority'] = get_tickets_field_value("priority", 'Medium')

    #     # TODO check other devices. Get their "last seen" to see if we can assume they have not checked in. Add results to body

    #         #'createDate': date,
    #         #'dueDateTime': due_date,
    #     return at._api_write("Tickets", params)
    # else:
    #     archive_alert(m_alert.unifi_alert_id)

def check_unifi_alert_for_relevants(m_alert, site):
    if m_alert.alert_time < datetime.today() - timedelta(days=1):
        print("          - Alert is old. Clearing alert")
        archive_unifi_alert(m_alert.unifi_alert_id)
        return False
    
    if "Lost_Contact" in m_alert.unifi_alert_key:
        if c.get_device_stat(m_alert.mac)['state'] == 1:
            print("          - Device state is active. Clearing alert.")
            archive_unifi_alert(m_alert.unifi_alert_id)
            return False
    if "EVT_GW_WANTransition" in m_alert.unifi_alert_key:
        print(site.desc)
        gateway = ((((m_alert.message).split()[0]).replace('Gateway','')).replace('[', '')).replace(']','')
        if c.get_device_stat(gateway)['state'] == 1:
            archive_unifi_alert(m_alert.unifi_alert_id)
            return False
   
    print(site.desc)
    print("Checking for relevants")
    print(m_alert.to_str())
    
    sys.exit()

def get_unifi_alert_device(alert):
    mac = None
    for key in alert:
        if alert['key'] == "EVT_GW_Lost_Contact":
            mac = alert['gw']
        elif alert['key'] == "EVT_GW_CommitError":
            mac = alert['gw']
        elif alert['key'] == "EVT_GW_CommitError":
            mac = alert['gw']
        elif alert['key'] == "EVT_GW_WANTransition":
            mac = alert['gw']
        elif alert['key'] == "EVT_AP_Lost_Contact":
            mac = alert['ap']
        elif alert['key'] == "EVT_SW_Lost_Contact":
            mac = alert['sw']
        elif alert['key'] == "EVT_SW_StpPortBlocking":
            mac = alert['sw']
        elif alert['key'] == "EVT_LTE_Lost_Contact":
            mac = alert['dev']
        elif alert['key'] == "EVT_XG_Lost_Contact":
            mac = alert['xg']

    if mac:
        mac_db = session.query( Devices_Macs ).filter_by(mac_addresses=mac ).first()
        device_db = session.query( Devices ).filter_by(primary_key=mac_db.device_key)
        return device_db, mac

def unifi_alerts():
    print(" - Processing UniFi 'Alerts/Alarms")
    # TODO Currently we only grab unarchived events, then archvie the event after to create a ticket. I would like to process all events based on date instead.
    # TODO Process unarchvied events
    # TODO Check for multiple events in the same day.
    unifi_controller_query = session.query( UniFi_Controllers ).filter_by(host=c.host ).first()
    # TODO change sites_query to only look up for this controller
    sites_query = session.query(  UniFi_Sites )
    for site in sites_query:
        unifi_site_query = session.query( UniFi_Sites ).filter_by(name=site.name, controller_key=unifi_controller_query.primary_key ).first()
        link_unifi_site = session.query( Link_UniFi_Companies ).filter_by( unifi_sites_key=unifi_site_query.primary_key ).first()
        
        company_key = 0
        if hasattr(link_unifi_site, "primary_key"): 
            company_key = link_unifi_site.companies_key
            link_autotask_company = session.query( Link_Autotask_Companies ).filter_by( companies_key=company_key).first()
            if hasattr(link_autotask_company, 'primary_key'):
                c.site_id = site.name
                alerts = c.get_alerts_unarchived()
                for alert in alerts:
                    m_alert = Alerts.from_unifi_dict(alert)
                    m_alert.at_company_id = link_autotask_company.id
                    m_alert.device_db, m_alert.mac = get_unifi_alert_device(alert)
                    alert_config = get_unifi_alert_config(m_alert.unifi_alert_key)
                    if alert_config is None:
                        print("          - No config for this alert. Skipping alert.")
                        sys.exit()
                    if alert_config['Create Ticket']:
                        if check_unifi_alert_for_relevants(m_alert, site):
                            reply = create_unifi_alert_ticket(m_alert, alert_config)
                            # TODO check the reply and respond to errors
                            sys.exit()
                            if reply != []:
                                archive_alert(m_alert.unifi_alert_id)

# TODO Move to pyunifi
def _api_url_v2():
    return c.url + "v2/api/site/" + c.site_id + "/"

# TODO Move to pyunifi
def _api_write_v2(url, params=None):
    return c._write(_api_url_v2() + url, params)

def unifi_system_logs():
    print(" - Checking System Logs")   
    # 1 hour = 1.00 	3,600,000
    furture_time = time.time_ns() // 1000000 - 3600000
    hour_past = 0
    params = {"timestampFrom": hour_past, "timestampTo": furture_time, "pageSize": 100, "categories": ["INTERNET", "POWER", "DEVICES", "SYSTEM"], "pageNumber": 0, "systemLogDeviceTypes": [
    	"GATEWAYS", "SWITCHES", "ACCESS_POINT", "SMART_POWER", "BUILDING_TO_BUILDING_BRIDGES", "UNIFI_LTE", "NON_NETWORK_DEVICES"]}
    # TODO Move to pyunifi
    syslogs = _api_write_v2("system-log/system-critical-alert", params)

    for syslog in syslogs:
        #event_config = None
        #create_ticket = True

        #print(syslog)
        #sys.exit()
        #m_alert = models.manifold_alert.from_unifi_syslog_dict(syslog)

        if syslog['key'] == "DEVICE_RECONNECTED_WITH_DOWNLINKS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_UNREACHABLE_WITH_DOWNLINKS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_RECONNECTED_SEVERAL_TIMES":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_RECONNECTED":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "DEVICE_UNREACHABLE":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "ISP_HIGH_LATENCY":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "ISP_PACKET_LOSS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "CLIENT_IP_CONFLICT":
            print(syslog['key'] + "-" + syslog['message'])
            print(syslog)
        elif syslog['key'] == "CLIENT_IP_CONFLICT_BULK":
            print(syslog['key'] + "-" + syslog['message'])
            print(syslog)
        elif syslog['key'] == "DEVICE_DISCOVERED" or syslog['key'] == "DEVICE_ADOPTED":
            pass
        elif syslog['key'] == "PORT_TRANSMISSION_ERRORS":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_FAILED_OVER_TO_BACKUP_LTE":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "RADIUS_SERVER_ISSUE":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_RETURNED_FROM_BACKUP_WAN":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_WAN_FAILED_MULTIPLE_TIMES":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "ULTE_WARNING_LIMIT_EXCEEDED":
            print(syslog['key'] + "-" + syslog['message'])
        elif syslog['key'] == "NETWORK_WAN_FAILED":
            print(syslog['key'] + "-" + syslog['message'])
        else:
            print(syslog['key'])
            print(syslog)
            sys.exit()


# TODO Move to pyunifi
def unifi_widget_warnings():
    return c._api_read("stat/widget/warnings")

# This could probably run once a day. Maybe once a week
def check_unifi_warnings():
    print(" - Checking 'warnings'")
    unifi_controller_query = session.query( UniFi_Controllers ).filter_by(host=c.host ).first()
    # TODO change sites_query to only look up for this controller
    sites_query = session.query(  UniFi_Sites )
    for site in sites_query:
        c.site_id = site.name
        warnings_list = unifi_widget_warnings()
        for warnings in warnings_list:
            for key, warning in warnings.items():
                if key == 'has_upgradable_devices':
                    if warning == True:
                        # TODO Need to find the device and create a ticket based with that device as a CI.
                        # TODO Maybe check if there is a schedule and autotmaticly put it in the schedule
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                # TODO Make active once we have an ignor list
                if key == 'has_wlan_overrides':
                    if warning == True:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        for device in c.get_aps():
                            if 'wlan_overrides' in device:
                                print(device['name'] + " " + str(device['wlan_overrides']))
                        sys.exit()


                if key == 'firmware_last_changed':
                    # This just gives a date. Not sure how useful this is.
                    pass
                if key == 'last_controller_update_query':
                    # This just gives a date. Not sure how useful this is.
                    pass
                if key == 'last_controller_update_query_status':
                    # This just gives us an 'ok' seems like it for the whole controller, so we probably only need to check it once.
                    pass
                if key == 'last_firmware_update_query':
                    # This just gives a date. Not sure how useful this is.
                    pass
                if key == 'last_firmware_update_query_status':
                    # Returns 'ok'. Not sure this is useful
                    pass
                if key == 'unsupported_device_count':
                    if warning > 0:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                if key == 'eol_device_count':
                    if warning > 0:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        unifi_devices = c.get_aps()
                        for unifi_device in unifi_devices:
                            if unifi_device['model_in_eol']:
                                print("      - " + site.desc + " " + unifi_device['name'] + " - " + unifi_device['mac'] + " - " + str(unifi_device['model_in_eol']))
                                sys.exit()
                if key == 'lts_device_count':
                    if warning > 0:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                if key == 'lte_subscription_past_due_for':
                    if warning != []:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                if key == 'lte_subscription_canceled_for':
                    if warning != []:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                if key == 'lte_subscription_check_required_for':
                    if warning != []:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                if key == 'controller_low_disk_space':
                    # Probably only need to do this once for everyone
                    if warning:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                if key == 'request_analytics_approvement':
                    # No idea what this is
                    if warning:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        sys.exit()
                if key == 'mdns_networks_limit':
                    if warning['exceeded']:
                        print("    - " + site.desc + " " + key + " " + str(warning))
                        

def unifi_toast():
    print("TODO Findout what creates the UI's 'Toast' and create tickets based on those")

def unifi_tickets_cleanup():
    print("TODO check exsiting tickets and update/close ones as needed")

    # TODO if ticket exist but doesn't need to
        # add note to ticket
        # if tasky channel
            # alert channel
        # else
            # if primary user
                # alert primary resource
            # else
                # alert resource(s) with time
        # if no time on ticket
            # Close ticket

def unifi_alerts_all():
    # TODO For loop through unifi controllers
    # Map which alerts get what contract in Autotask. Default is site down, always alert. All other alerts only happen if they have an Autotask SLA contract
    # TODO We currently track tickets based on issueType/SubIssueType and maybe the CI in Autotask. This should change to the ticket being tracked in a database until closed
    print("UniFi Alerts - All")
    unifi_device_status()
    unifi_alerts()
    unifi_system_logs()
    check_unifi_warnings()
    #unifi_toast()
    #unifi_tickets_cleanup()
    # TODO month check for lost conection devices for non-sla cusomters. Maybe it sends them an email instead of creating a ticket

def _sync_unifi_sites(tenant=None):
    print("Syncing UniFi Sites")
    if tenant is None:
        tenant = UniFi_Controllers(
            host = config.UnifiHost,
            port = config.UnifiPort
        )
        session.add(tenant)
        session.flush()
        session.refresh(tenant)

    siteslist = c.sites_get()

    for site in siteslist.results:
        sites_query = session.query( UniFi_Sites ).filter_by(id=site.id, controller_key = tenant.primary_key ).first()

        if hasattr(sites_query, 'id'):
            if sites_query.name != site.name:
                sites_query.name = site.name
            if sites_query.id != site.id:
                sites_query.id = site.id
            if sites_query.desc != site.desc:
                sites_query.desc = site.desc
        else:
            sites_obj = UniFi_Sites(
                name = site.name,
                id = site.id,
                desc = site.desc,
                controller_key = tenant.primary_key
            )
            session.add(sites_obj)
    print("TODO need to verify UniFi Site has a contract. Send notification if not")
    tenant.last_full_sync = datetime.now()
    session.commit()
    return siteslist

def get_unifi_sites():
    sites = session.query( UniFi_Sites ).all()
    siteslist = pyunifi.models.Siteslist()
    
    if sites:
        sites_list = []
        for site in sites:
            sites_list.append(pyunifi.models.Site(
                    anonymous_id = site.anonymous_id,
                    name = site.name,
                    id = site.id,
                    desc = site.desc,
                    role = site.role,
                    device_count = site.device_count
                    )
            )
        siteslist = pyunifi.models.Siteslist(sites_list)
    else:
        siteslist = _sync_unifi_sites()

    session.close()
    return siteslist

# TODO Move to pyunifi
def get_unifi_devices_basic():
    """ Return a list of all devices """
    return c._api_read("stat/device-basic/")

def sync_unifi_devices():
    # TODO Add a check for EOL devices
    print(" - Syncing UniFi Devices")
    unifi_controller_query = session.query( UniFi_Controllers ).filter_by(host=c.host ).first()
    # TODO change sites_query to only look up for this controller
    sites_query = session.query(  UniFi_Sites )
    for site in sites_query:
        unifi_site_query = session.query( UniFi_Sites ).filter_by(name=site.name, controller_key=unifi_controller_query.primary_key ).first()
        link_unifi_site = session.query( Link_UniFi_Companies ).filter_by( unifi_sites_key=unifi_site_query.primary_key ).first()
        company_key = 0
        if hasattr(link_unifi_site, "primary_key"): company_key = link_unifi_site.companies_key
        c.site_id = site.name
        unifi_devices_json = c.get_aps()
        for unifi_device in unifi_devices_json:
            if unifi_device['adopted'] == True and 'serial' in unifi_device:
                db_obj = session.query( Devices ).filter_by(serial=unifi_device['serial'], manufacturer="Ubiquiti").first()
                if hasattr(db_obj, 'primary_key'):
                    channel_sync_device = {}
                    if db_obj.name != unifi_device['name']:
                        db_obj.name = unifi_device['name']
                        channel_sync_device['name'] = unifi_device['name']
                        session.add(db_obj)
                    if unifi_device['config_network']['type'] != 'dhcp':
                        if db_obj.ip_addresses != unifi_device['ip']:
                            db_obj.ip_addresses = unifi_device['ip']
                            channel_sync_device['ipaddress'] = unifi_device['ip']
                            session.add(db_obj)
                    # add macs here
                    if db_obj.manufacturer != "Ubiquiti":
                        db_obj.manufacturer = "Ubiquiti"
                        channel_sync_device['manufacturer'] = "Ubiquiti"
                        session.add(db_obj)
                    if db_obj.model != unifi_device['model']:
                        db_obj.model = unifi_device['model']
                        channel_sync_device['model'] = unifi_device['model']
                        session.add(db_obj)
                    macs_db_obj = session.query( Devices_Macs ).filter_by(device_key=db_obj.primary_key ).all()
                    if len(macs_db_obj) > 0:
                        mac_list = []
                        found = 0
                        for mac in macs_db_obj:
                            if mac.mac_addresses == unifi_device['mac']: found = 1
                        
                        if found == 0:
                            macs_db_obj = Devices_Macs(
                                mac_addresses = unifi_device['mac'],
                                device_key = db_obj.primary_key
                            )
                            mac_list.append(unifi_device['mac'])
                            channel_sync_device['macs'] = mac_list
                            session.add(macs_db_obj)
                    else:
                        macs_db_obj = Devices_Macs(
                            mac_addresses = unifi_device['mac'],
                            device_key = db_obj.primary_key,
                        )
                        mac_list.append(unifi_device['mac'])
                        channel_sync_device['macs'] = mac_list
                        session.add(macs_db_obj)
                    link_db_obj = session.query( Link_UniFi_Devices ).filter_by( device_key=db_obj.primary_key ).first()
                    if hasattr(link_db_obj, 'primary_key'):
                        if link_db_obj.unifi_sites_key != unifi_site_query.primary_key:
                            link_db_obj.unifi_sites_key = unifi_site_query.primary_key
                            session.add(link_db_obj)
                    else:
                        link_db_obj = Link_UniFi_Devices(
                            device_key = db_obj.primary_key,
                            unifi_sites_key = unifi_site_query.primary_key
                        )
                        session.add(link_db_obj)
                    if channel_sync_device: 
                        if db_obj.company_key != 0:
                            sync_channels(unifi_controller_query, db_obj, channel_sync_device)
                else:
                    channel_sync_device = {}
                    db_obj = Devices(
                        name = unifi_device['name'],
                        serial = unifi_device['serial'],
                        ip_addresses = unifi_device['ip'],
                        manufacturer = "Ubiquiti",
                        model = unifi_device['model'],
                        company_key = company_key
                    )
                    channel_sync_device['name'] = unifi_device['name']
                    channel_sync_device['serial'] = unifi_device['serial']
                    channel_sync_device['ip_addresses'] = unifi_device['ip']
                    channel_sync_device['manufacturer'] = "Ubiquiti"
                    channel_sync_device['model'] = unifi_device['model']
                    channel_sync_device['company_key'] = company_key


                    session.add(db_obj)
                    session.flush()
                    session.refresh(db_obj)
                    mac_list = []
                    macs_db_obj = Devices_Macs(
                            mac_addresses = unifi_device['mac'],
                            device_key = db_obj.primary_key,
                    )
                    mac_list.append(unifi_device['mac'])
                    channel_sync_device['macs'] = mac_list
                    session.add(macs_db_obj)

                    link_db_obj = Link_UniFi_Devices(
                        device_key = db_obj.primary_key,
                        unifi_sites_key = unifi_site_query.primary_key
                    )
                    session.add(link_db_obj)
                    session.commit()
                    if channel_sync_device: 
                        if db_obj.company_key != 0:
                            sync_channels(unifi_controller_query, db_obj, channel_sync_device)
    session.commit()

def sync_unifi_clients():
    print("TODO Sync UniFi Clients")

def update_autotask_last_sync():
    print("Autotask Sync")
    # TODO move to a for loop once tenant information has moved from config to the DB
    tenant = session.query( Autotask_Tenants ).filter_by(api_user=config.atUsername).first()
    if tenant:
        # TODO currently set to 4 hours, but that should be configurable
        if (datetime.now() - tenant.last_full_sync).total_seconds() / 3600 > 4:
            _sync_autotask_companies(tenant)
        if (datetime.now() - tenant.last_full_sync).total_seconds() / 3600 > 24:
            _sync_autotask_ci_catagories()
            _sync_autotask_ci_types()
            _sync_autotask_products()
            sync_autotask_devices()
            _sync_autotask_contracts()
            get_autotask_tickets_entity_information()
    else:
        _sync_autotask_companies()
        _sync_autotask_ci_catagories()
        _sync_autotask_ci_types()
        _sync_autotask_products()
        sync_autotask_devices()
        _sync_autotask_contracts()
        get_autotask_tickets_entity_information()

def get_autotask_tickets_field_value(name, lable):
    for field in tickets_entity_information_fields:
        if field['name'] == name:
            for picklistValue in field['picklistValues']:
                if picklistValue['label'] == lable:
                    return str(picklistValue['value'])

def get_autotask_ci_hostname(ci):
    if ci['rmmDeviceAuditHostname']:
        return ci['rmmDeviceAuditHostname']
    elif ci['dattoHostname']:
        return ci['dattoHostname']
    elif ci['referenceTitle']:
        return ci['referenceTitle']
    else:
        return None

def get_autotask_ci_manufacturer_model(ci):
    # TODO Only look up products as we need them. Then put then in the database
    product = session.query( Autotask_Products ).filter_by(id=ci['productID']).first()
    if product:
        return product.manufacturerName, product.manufacturerProductName
    else:
        url = "Products/" + str(ci['productID'])
        autotask_product = at._api_read(url)['item']
        db_obj = Autotask_Products(
            id = str(ci['productID']),
            description = autotask_product['description'],
            manufacturerName = autotask_product['manufacturerName'],
            manufacturerProductName = autotask_product['manufacturerProductName'],
            productCategory = autotask_product['productCategory']
        )
        session.add(db_obj)
        session.commit()
        return db_obj.manufacturerName, db_obj.manufacturerProductName

def convert_at_datetime(date_time):
    return dateutil.parser.isoparse(date_time)

def _sync_autotask_contracts():
    # TODO Fix get_all_contracts to allow include_fields to limit data we are pulling from autotask
    include_fields = "'endDate','startDate','contactID','contactName','companyID','status'"
    contracts = at.get_all_contracts()
    for contract in contracts:
        tenant = session.query( Autotask_Tenants ).filter_by( host=at.host ).first()
        link_autotask_company = session.query( Link_Autotask_Companies ).filter_by( id=contract['companyID'],autotask_tenant_key=tenant.primary_key ).first()
        contract_db_obj = session.query( Autotask_Contracts ).filter_by( autotask_id=contract['id'], company_key=link_autotask_company.companies_key, autotask_tenant_key=tenant.primary_key ).first()
        if contract_db_obj:
            print("check for updates in database")
            sys.exit()
        else:
            db_obj = Autotask_Contracts(
                autotask_id = contract['id'],
                company_key = link_autotask_company.companies_key,
                startDate = convert_at_datetime(contract['startDate']),
                endDate = convert_at_datetime(contract['endDate']),
                contractName = contract['contractName'],
                autotask_tenant_key = tenant.primary_key
            )
            session.add(db_obj)
            session.commit()

def sync_autotask_devices():
    print(" - Syncing Devices to Autotask")
    tenant = session.query( Autotask_Tenants ).filter_by(host=config.atHost ).first()
    # TODO add filter for tenant
    companies = session.query( Companies ).all()
    for company in companies:
        print(" - Syncing devices for " + company.company_name)
        link_autotask_company = session.query( Link_Autotask_Companies ).filter_by(companies_key=company.primary_key).first()
        if hasattr(link_autotask_company, 'primary_key'):
            autotask_id = link_autotask_company.id
            company_filter = at.create_filter("eq", "companyID", str(autotask_id)) + "," + at.create_filter("eq", "isActive", "True")
            company_includes = '"id","configurationItemCategoryID","companyID","configurationItemType","dattoHostname","productID","referenceTitle","rmmDeviceAuditDescription","rmmDeviceAuditIPAddress","rmmDeviceAuditHostname","rmmDeviceAuditMacAddress","serialNumber"'
            cis = at._api_read("ConfigurationItems" + "/query?search={'IncludeFields':[" + company_includes + "], 'filter':[" + company_filter + ']}')

            for ci in cis:
                manufacturer, model = get_autotask_ci_manufacturer_model(ci)
                device_db_obj = session.query( Devices ).filter_by(manufacturer=manufacturer, serial=ci['serialNumber']).first()
                autotask_product = None
                if ci['productID']:
                    autotask_product = session.query( Autotask_Products ).filter_by(id=ci['productID']).first()
                if ci['dattoHostname'] or ci['referenceTitle'] or ci['rmmDeviceAuditHostname'] or ci['serialNumber'] or ci['rmmDeviceAuditMacAddress']:
                    if device_db_obj:
                        link_unifi_device = session.query( Link_UniFi_Devices ).filter_by( device_key=device_db_obj.primary_key ).first()
                        # TODO look up link)unifi_devices and see if the device is in there
                        if link_unifi_device:

                            print("Sync back to Autotask. UniFi is primary")
                        else:
                            channel_sync_device = {}
                            hostname = get_autotask_ci_hostname(ci)
                            if device_db_obj.name != hostname:
                                device_db_obj.name = hostname
                                channel_sync_device['name'] = hostname
                                session.add(device_db_obj)
                            if device_db_obj.description != ci['rmmDeviceAuditDescription']:
                                device_db_obj.description = ci['rmmDeviceAuditDescription']
                                channel_sync_device['description'] = ci['rmmDeviceAuditDescription']
                                session.add(device_db_obj)
                            if device_db_obj.serial != ci['serialNumber']:
                                device_db_obj.serial = ci['serialNumber']
                                channel_sync_device['serialNumber'] =  ci['serialNumber']
                                session.add(device_db_obj)
                            if device_db_obj.manufacturer != manufacturer:
                                device_db_obj.manufacturer = manufacturer
                                channel_sync_device['manufacturer'] =  manufacturer
                                session.add(device_db_obj)
                            if device_db_obj.model != model:
                                device_db_obj.model = model
                                channel_sync_device['model'] =  model
                                session.add(device_db_obj)

                            macs_db_obj = session.query( Devices_Macs ).filter_by(device_key=device_db_obj.primary_key ).all()
                            if ci['rmmDeviceAuditMacAddress']:
                                if len(macs_db_obj) > 0:
                                    mac_list = []
                                    found = 0
                                    for mac in macs_db_obj:
                                        if mac.mac_addresses == ci['rmmDeviceAuditMacAddress']: found = 1
                                    
                                    if found == 0:
                                        macs_db_obj = Devices_Macs(
                                            mac_addresses = (ci['rmmDeviceAuditMacAddress']).strip(),
                                            device_key = device_db_obj.primary_key
                                        )
                                        mac_list.append((ci['rmmDeviceAuditMacAddress']).strip())
                                        channel_sync_device['macs'] = mac_list
                                        session.add(macs_db_obj)
                                else:
                                    macs_db_obj = Devices_Macs(
                                        mac_addresses = (ci['rmmDeviceAuditMacAddress']).strip(),
                                        device_key = device_db_obj.primary_key,
                                    )
                                    mac_list.append((ci['rmmDeviceAuditMacAddress']).strip())
                                    channel_sync_device['macs'] = mac_list
                                    session.add(macs_db_obj)
                            link_db_obj = session.query( Link_Autotask_Devices ).filter_by( device_key=device_db_obj.primary_key ).first()
                            if hasattr(link_db_obj, 'primary_key'):
                                if link_db_obj.autotask_tenant_key != tenant.primary_key:
                                    link_db_obj.autotask_tenant_key = tenant.primary_key
                                    session.add(link_db_obj)
                            else:
                                link_db_obj = Link_Autotask_Devices(
                                    device_key = db_obj.primary_key,
                                    autotask_tenant_key = tenant.primary_key
                                )
                                session.add(link_db_obj)
                            if channel_sync_device: 
                                if device_db_obj.company_key != 0:
                                    sync_channels(tenant, device_db_obj, channel_sync_device)
                            session.commit()
                    else:
                        db_obj = Devices(
                            name = ci['referenceTitle'],
                            serial = ci['serialNumber'],
                            #ip_addresses = unifi_device['ip'],
                            company_key = company.primary_key
                        )
                        if hasattr(autotask_product, "manufacturerName"): db_obj.manufacturer = autotask_product.manufacturerName
                        if hasattr(autotask_product, "manufacturerProductName"): db_obj.manufacturer = autotask_product.manufacturerProductName

                        session.add(db_obj)
                        session.flush()
                        session.refresh(db_obj)
                        
                        # TODO Add a place to lookup client UDF for Mac addresses
                        if ci['rmmDeviceAuditMacAddress']:
                            for mac in ci['rmmDeviceAuditMacAddress'].split(","):
                                macs_db_obj = None
                                if mac:
                                    macs_db_obj = Devices_Macs(
                                        mac_addresses = mac.strip(),
                                        device_key = db_obj.primary_key
                                    )
                                    session.add(macs_db_obj)

                        link_db_obj = Link_Autotask_Devices(
                            device_key = db_obj.primary_key,
                            autotask_tenant_key = tenant.primary_key,
                            company_key = company.primary_key
                        )
                        session.add(link_db_obj)
                        session.flush()
                        if db_obj.company_key != 0:
                            sync_channels(tenant, db_obj)

                        session.commit()

    session.commit()

def _sync_autotask_ci_types():
    print(" - Syncing CI Types")
    ci_entities_json = at._api_read("ConfigurationItems/entityInformation/fields/")['fields']
    keep_list = ['configurationItemType']
    for field in ci_entities_json:
        if field['name'] == 'configurationItemType':
            if field['picklistValues'] is not None:
                for value in field['picklistValues']:
                    query = session.query(  Autotask_CI_Types ).filter_by(value=value['value']).first()
                    if hasattr(query, 'value'):
                        if query.value != value['value']:
                            query.value = value['value']
                        if query.label != value['label']:
                            query.label = value['label']
                        session.add(query)
                    else:
                        db_obj = Autotask_CI_Types(
                            value = value['value'],
                            label = value['label']
                        )
                    session.add(db_obj)
    session.commit()

def _sync_autotask_ci_catagories():
    print(" - Syching CI Catagories")
    ci_categories = at.get_ci_categories()
    
    for ci_category in ci_categories:
        query = session.query(  Autotask_CI_Catagories ).filter_by(id=ci_category['id']).first()
        if hasattr(query, 'id'):
            if query.name != ci_category['name']:
                query.name = ci_category['name']
                session.add(query)
        else:
            ci_categories_db_obj = Autotask_CI_Catagories(
                name = ci_category['name'],
                id = ci_category['id'],
            )
            session.add(ci_categories_db_obj)
    session.commit()

def _sync_autotask_products():
    print(" - Syncing Products")
    # TODO Only look up products as we need them, then store them in our database. This function will just be to check to see if the products in the database has changed.
    products = at.get_products()

    for product in products:
        query = session.query( Autotask_Products ).filter_by(id=product['id']).first()
        if hasattr(query, 'id'):
            if query.id != product['id']:
                query.id != product['id']
                session.add(query)
            if query.description != product['description']:
                query.description = product['description']
                session.add(query)
            if query.manufacturerName != product['manufacturerName']:
                query.manufacturerName = product['manufacturerName']
                session.add(query)
            if query.manufacturerProductName != product['manufacturerProductName']:
                query.manufacturerProductName = product['manufacturerProductName']
                session.add(query)
            if query.productCategory != product['productCategory']:
                query.productCategory = product['productCategory']
                session.add(query)
        else:
            db_obj = Autotask_Products(
                id = product['id'],
                description = product['description'],
                manufacturerName = product['manufacturerName'],
                manufacturerProductName = product['manufacturerProductName'],
                productCategory = product['productCategory']
            )
            session.add(db_obj)
    session.commit()

def _sync_autotask_companies(tenant=None):
    print(" - Sync Autotask Companies")
    if tenant is None:
        tenant = Autotask_Tenants(
            host = config.atHost,
            api_user = config.atUsername
        )
        session.add(tenant)
        session.flush()
        session.refresh(tenant)

    # TODO change this to for loop all of the tenants of Autotask
    # TODO add include_fields here to only give the data we are asking for. Currently that is just id, companyName, companyNumber
    autotask_companies_json = at.get_companies()
    
    # TODO if a company gets removed, this will not detect it. Create fuction to detect company remocal. Update unifi sites too
    for autotask_company in autotask_companies_json:
        company_db_obj = None
        link_autotask_companies_db_query_obj = session.query(  Link_Autotask_Companies ).filter_by(id=autotask_company['id']).first()

        if hasattr(link_autotask_companies_db_query_obj, 'id'):
            company_db_obj = session.query( Companies ).filter_by(primary_key=link_autotask_companies_db_query_obj.companies_key).first()
            if autotask_company['companyName'] != company_db_obj.company_name:
                company_db_obj.company_name = autotask_company['companyName']
                session.add(company_db_obj)
            if autotask_company['companyNumber'] != company_db_obj.company_number:
                company_db_obj.company_number = autotask_company['companyNumber']
                session.add(company_db_obj)
        else:
            company_db_obj = session.query( Companies ).filter_by(company_name=autotask_company['companyName']).first()
            if not company_db_obj:
                company_db_obj = Companies(
                    company_name = autotask_company['companyName'],
                    company_number = autotask_company['companyNumber']
                )
                session.add(company_db_obj)
                session.flush()
                session.refresh(company_db_obj)

            link_autotask_companies_db_obj = Link_Autotask_Companies(
                companies_key = company_db_obj.primary_key,
                autotask_tenant_key = tenant.primary_key,
                id = autotask_company['id']
             )
            session.add(link_autotask_companies_db_obj)
            session.commit()

        # TODO this needs to be configurable. If we are going to keep it in Autotask, then we need to add a UDF for the UniFi Controllers url
        unifi_site_name = None
        unifi_tenant = session.query( UniFi_Controllers ).filter_by(host=config.UnifiHost).first()

        for udf in autotask_company['userDefinedFields']:
            if udf['name'] == 'Unifi Site ID':
                unifi_site_name = udf['value']
                break
        if unifi_site_name:
            sites_query = session.query(  UniFi_Sites ).filter_by(name=unifi_site_name, controller_key = unifi_tenant.primary_key ).first()
            if hasattr(sites_query, 'primary_key'):
                # TODO Need to check for more than 1 site
                link_unifi_sites_db_obj = session.query( Link_UniFi_Companies ).filter_by(companies_key=autotask_company['id']).first()
                if hasattr(link_unifi_sites_db_obj, 'primary_key'):
                    if link_unifi_sites_db_obj.unifi_sites_key != sites_query.primary_key:
                        link_unifi_sites_db_obj.unifi_sites_key = sites_query.primary_key
                        session.add(link_unifi_sites_db_obj)
                else:
                    link_unifi_sites_db_obj = Link_UniFi_Companies(
                        companies_key = company_db_obj.primary_key,
                        unifi_sites_key = sites_query.primary_key,
                    )
                    session.add(link_unifi_sites_db_obj)
                    session.flush()
                    session.refresh(link_unifi_sites_db_obj)
 
    tenant.last_full_sync = datetime.now()
    session.commit()
    return autotask_companies_json

def get_autotask_companies():
    # TODO need to create a autotask company object and convert the database object to that
    return session.query( Autotask_Companies ).all()

if __name__ == "__main__":
    main()



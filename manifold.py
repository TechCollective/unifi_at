#!/usr/bin/env python
import requests
import json
import csv
import sys
import time
from datetime import datetime, timedelta
import dateutil.parser
#from pyunifi.controller import Controller # TechCollective's feature branch
import pyunifi
#config file within the same directory
import config
from pyautotask.atsite import atSite
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import *
#import models

# TODO Move this to the unifi_controllers database
c = pyunifi.controller.Controller(config.UnifiHost, config.UnifiUsername, config.UnifiPassword, config.UnifiPort, "v5")
# TODO Move this to the autotask_tenants database
at = atSite(config.atHost, config.atUsername, config.atPassword, config.atAPIInterationcode)

engine = create_engine('sqlite:///manifold.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# TODO Check Autotask contract. Unifi Site Description get assigned from Autotask "companyNumber - companyName". If they don't have a contract, they get the prefix name in UniFi with zz-$
def main():
    update_last_sync()
    #autotask_companies = get_autotask_companies()
    #unifi_sites_obj = get_unifi_sites()
    
    
def update_last_sync():
    update_autotask_last_sync()
    #update_unifi_last_sync()

def update_unifi_last_sync():
    controller = session.query( UniFi_Controller ).filter_by(host=config.UnifiHost).first()
    if controller:
        # TODO currently set to 4 hours, but that should be configurable
        if (datetime.now() - controller.last_sync).total_seconds() / 3600 > 4:
            _sync_unifi_sites()
    else:
        _sync_unifi_sites()

def _sync_unifi_sites():
    siteslist = c.sites_get()
    # TODO need to compare and update. or only delete sites from a controller. So we can track multiple controllers
    session.query(UniFi_Sites).delete()

    for site in siteslist.results:
        site_obj = UniFi_Sites(
            anonymous_id=site.anonymous_id,
            name=site.name,
            id=site.id,
            desc=site.desc,
            role=site.role,
            device_count=site.device_count
        )
        session.add(site_obj)
    controller = session.query( UniFi_Controller ).filter_by(host=config.UnifiHost)
    controller.last_sync = datetime.now()
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

def update_autotask_last_sync():
    tenant = session.query( Autotask_Tenants ).filter_by(api_user=config.atUsername).first()
    if tenant:
        # TODO currently set to 4 hours, but that should be configurable
        if (datetime.now() - controller.last_sync).total_seconds() / 3600 > 4:
            _sync_autotask_companies()
    else:
        _sync_autotask_companies()

def _sync_autotask_companies():
    # TODO we should have 2 last_sync for each Autotask. 1 for last full sync. 1 for partial syncs. More syncs should be partial and we only request for Autotask Companies createDate, lastActivityDate and lastTrackedModifiedDateTime is newer than last_sync
    # TODO Filter for isActive as well
    filter_fields = "{'op': 'eq', 'field': 'isActive', 'value': 1}"

    # TODO change this to for loop all of the tenants of Autotask
    autotask_companies_json = at.get_companies(filter_fields)
    
    # TODO need to compare and update. or only delete companies from one tenant. So we can track multiple autotant tenants
    #session.query(Autotask_Companies).delete()
    #session.query( Link_Autotask_UniFi ).delete()
    for autotask_company in autotask_companies_json:
        company_db_query_obj = session.query( Companies ).filter_by(company_name=autotask_company['companyName']).first()
        
        if company_db_query_obj:
            print(company_db_query_obj.company_name)
            sys.exit()
            #company_name = Column(String, unique=True)
            #company_number = Column(String, unique=True)
            #unifi_site: Mapped["UniFi_Sites"] = relationship()
        else:
            company_db_obj = Companies(
                company_name = autotask_company['companyName'],
                company_number = autotask_company['companyNumber']
            )
            session.add(company_db_obj)
            unifi_site_name = None
            for udf in autotask_company['userDefinedFields']:
                if udf['name'] == 'Unifi Site ID':
                    unifi_site_name = udf['value']
                    break
            #link_unifi_sites_db_obj = Link_UniFi_Sites(
            #    companies_key = ,
            #    unifi_sites_key = ,
            #    name = unifi_site_name
            #)
        
        
        company_obj = Autotask_Companies(
            id = company['id'],
            company_name = company['companyName']
        )
        session.add(company_obj)
        unifi_site_id = None
        for udf in company['userDefinedFields']:
            if udf['name'] == 'Unifi Site ID':
                unifi_site_id = udf['value']
                break
        unifi_site_obj = session.query( UniFi_Sites ).filter_by(name=unifi_site_id).first()
        autotask_company_obj = session.query( Autotask_Companies ).filter_by(id=company['id']).first()
        # TODO need to create a relationship for this table
        if unifi_site_obj:
            link_obj = Link_Autotask_UniFi(
                unifi_key = unifi_site_obj.primary_key,
                autotask_key = autotask_company_obj.primary_key
            )

    tenant = session.query( Autotask_Tenants ).filter_by(api_user=config.atUsername)    
    tenant.last_sync = datetime.now()
    session.commit()
    return companies_json

def get_autotask_companies():
    # TODO need to create a autotask company object and convert the database object to that
    return session.query( Autotask_Companies ).all()


if __name__ == "__main__":
    main()



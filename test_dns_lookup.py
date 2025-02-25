import os.path
import re

import dns.resolver


domains =[
    
    "asdavip.com",
    "asnomall.top",
    "aigoshop.vip",
    "adif-usd.com",
    "app.sparmall.vip",
    "www.lolex.net",
    "www.diamondzbear.com.capitolyieldsecurity.com"
    
    
]


import dns.message
import dns.query
import dns.rcode
import dns.exception

def get_dns_status(domain, nameserver='8.8.8.8'):
    """
    Perform DNS lookups for both A and AAAA records. 
    Returns:
        - 'NOERROR' if at least one record type returns NOERROR with a non-empty answer
        - None if a timeout or any other error occurs, or if no valid A/AAAA record is found
    """
    try:
        # 1) Query for A record
        query_a = dns.message.make_query(domain, 'A')
        response_a = dns.query.udp(query_a, nameserver, timeout=2)
        status_code_a = response_a.rcode()

        # Check if NOERROR and we got at least one answer section
        if status_code_a == dns.rcode.NOERROR and any(response_a.answer):
            print(f"Domain: {domain} - Status: NOERROR - Found A record(s)")
            return 'NOERROR'
        
        # 2) If we didn't find a valid A record, check AAAA
        query_aaaa = dns.message.make_query(domain, 'AAAA')
        response_aaaa = dns.query.udp(query_aaaa, nameserver, timeout=2)
        status_code_aaaa = response_aaaa.rcode()

        if status_code_aaaa == dns.rcode.NOERROR and any(response_aaaa.answer):
            print(f"Domain: {domain} - Status: NOERROR - Found AAAA record(s)")
            return 'NOERROR'

        # If we reach here, either the status wasn't NOERROR or no IP records were found
        print(f"Domain: {domain} - No valid A or AAAA records found ("
              f"A status: {dns.rcode.to_text(status_code_a)}, "
              f"AAAA status: {dns.rcode.to_text(status_code_aaaa)})")
        return None

    except dns.exception.Timeout:
        print(f"DNS query timed out for {domain}")
        return None
    except Exception as e:
        print(f"DNS query unexpected error for {domain}: {e}")
        return None



def main(domains):
    for domain in domains:
        get_dns_status(domain)
        
        
main(domains)
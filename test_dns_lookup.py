import os.path
import re

import dns.resolver

import pandas as pd


import dns.message
import dns.query
import dns.rcode
import dns.exception
import dns.message
import dns.query
import dns.rcode
import dns.exception
import dns.rdatatype

def get_dns_status_and_ip(domain, nameserver='8.8.8.8'):
    """
    Perform DNS lookups for both A and AAAA records.
    
    Returns:
        - ("NOERROR", <ip_address>) if at least one A or AAAA record returns NOERROR 
          with a non-empty answer, where <ip_address> is the first IP found.
        - None if a timeout or any other error occurs, or if no valid A/AAAA record is found.
    """
    def get_first_ip_from_answer(response):
        """
        Given a DNS response, return the first A or AAAA IP address found in the
        answer section. Returns None if no A/AAAA record is found.
        """
        for rrset in response.answer:
            for rr in rrset:
                # Check if we have an A record
                if rr.rdtype == dns.rdatatype.A:
                    return rr.address  # e.g. '1.2.3.4'
                # Or an AAAA record
                if rr.rdtype == dns.rdatatype.AAAA:
                    return rr.address  # e.g. '2001:db8::1'
        return None

    try:
        # 1) Query for A record
        query_a = dns.message.make_query(domain, 'A')
        response_a = dns.query.udp(query_a, nameserver, timeout=2)
        status_code_a = response_a.rcode()

        # Check if NOERROR and we got at least one A record
        if status_code_a == dns.rcode.NOERROR and response_a.answer:
            first_ip = get_first_ip_from_answer(response_a)
            if first_ip:
                print(f"Domain: {domain} - Status: NOERROR - Found A record: {first_ip}")
                return ("NOERROR", first_ip)

        # 2) If we didn't find a valid A record, check AAAA
        query_aaaa = dns.message.make_query(domain, 'AAAA')
        response_aaaa = dns.query.udp(query_aaaa, nameserver, timeout=2)
        status_code_aaaa = response_aaaa.rcode()

        if status_code_aaaa == dns.rcode.NOERROR and response_aaaa.answer:
            first_ip = get_first_ip_from_answer(response_aaaa)
            if first_ip:
                print(f"Domain: {domain} - Status: NOERROR - Found AAAA record: {first_ip}")
                return ("NOERROR", first_ip)

        # If we reach here, either the status wasn't NOERROR or no IP records were found
        print(
            f"Domain: {domain} - No valid A or AAAA records found "
            f"(A status: {dns.rcode.to_text(status_code_a)}, "
            f"AAAA status: {dns.rcode.to_text(status_code_aaaa)})"
        )
        return None

    except dns.exception.Timeout:
        print(f"DNS query timed out for {domain}")
        return None
    except Exception as e:
        print(f"DNS query unexpected error for {domain}: {e}")
        return None




def main():
    df = pd.read_csv("kraken_domains.csv")
    df = df.drop_duplicates(subset='Task Domain')
    df_2 = pd.DataFrame(columns = ['URLs'])
   
    # Open the file in write mode
    for domain in df["Task Domain"]:
            result = get_dns_status_and_ip(domain)
            if result:
                status, ip_address = result
                df_2.loc[len(df_2)] = domain
                # Write the domain, status, and IP to the file
            else:
                # Write a message indicating no valid records found
                pass
            
    df_2.to_csv("300_WF_domains.csv", index= False)
        
        
main()
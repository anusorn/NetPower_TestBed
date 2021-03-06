import sys
import numpy
sys.path.append("./")

from cyber_network.network_configuration import NetworkConfiguration
from cyber_network.traffic_flow import EmulatedTrafficFlow
from cyber_network.traffic_flow import TRAFFIC_FLOW_PERIODIC, TRAFFIC_FLOW_EXPONENTIAL, TRAFFIC_FLOW_ONE_SHOT
from cyber_network.network_scan_event import NetworkScanEvent
from cyber_network.network_scan_event import NETWORK_SCAN_NMAP_PORT
from core.net_power import NetPower
from core.shared_buffer import *
from utils.dnp3_pcap_post_processing import DNP3PCAPPostProcessing

ENABLE_TIMEKEEPER = 0
TDF = 10

# set of CPUs to run emulation/replay processes on when timekeeper is not
# enabled
CPUS_SUBSET = "2-3"


class TimeKeeperIntegration(NetPower):

    def __init__(self,
                 run_time,
                 network_configuration,
                 script_dir,
                 base_dir,
                 replay_pcaps_dir,
                 log_dir,
                 emulated_background_traffic_flows,
                 emulated_network_scan_events,
                 emulated_dnp3_traffic_flows):

        super(
            TimeKeeperIntegration,
            self).__init__(
            run_time,
            network_configuration,
            script_dir,
            base_dir,
            replay_pcaps_dir,
            log_dir,
            emulated_background_traffic_flows,
            emulated_network_scan_events,
            emulated_dnp3_traffic_flows,
            ENABLE_TIMEKEEPER,
            TDF,
            CPUS_SUBSET)


def get_network_configuration():

    network_configuration = NetworkConfiguration("ryu",
                                                 "127.0.0.1",
                                                 6633,
                                                 "http://localhost:8080/",
                                                 "admin",
                                                 "admin",
                                                 "clique_enterprise",
                                                 {"num_switches": 5,
                                                  "per_switch_links": 2,
                                                  "num_hosts_per_switch": 1,
                                                  "switch_switch_link_latency_range": (1, 1),
                                                  "host_switch_link_latency_range": (1, 1)
                                                  },
                                                 conf_root="configurations/",
                                                 synthesis_name="SimpleMACSynthesis",
                                                 synthesis_params={},
                                                 # Can map multiple power
                                                 # simulator objects to same
                                                 # cyber node.
                                                 roles=[
                                                     # internal field bus
                                                     # network. clique topology
                                                     # structure created only
                                                     # for this
                                                     ("controller_node",
                                                      ["control;1"]),
                                                     ("pilot_buses_set_1",
                                                      ["2", "25", "29"]),
                                                     ("pilot_buses_set_2",
                                                      ["22", "23", "19"]),
                                                     ("pilot_buses_set_3", [
                                                      "20", "10", "6", "9"]),
                                                     ("generator",
                                                      ["30;1", "31;1", "32;1",
                                                       "33;1", "34;1", "35;1",
                                                       "36;1", "37;1", "38;1",
                                                       "39;1"]),

                                                     # part of enterprise
                                                     # network. Linear topology
                                                     # which is attached to the
                                                     # clique at one switch
                                                     ("enterprise-1",
                                                      ["vpn-gateway;1"]),
                                                     ("enterprise-2",
                                                      ["attacker;1"])

                                                 ],
                                                 project_name="timekeeper_integration",
                                                 power_simulator_ip="127.0.0.1"
                                                 )

    network_configuration.setup_network_graph(
        mininet_setup_gap=1, synthesis_setup_gap=1)

    return network_configuration


def measure_dnp3_latencies(project_name, pcap_file_name):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    idx = script_dir.index('NetPower_TestBed')
    base_dir = script_dir[0:idx] + "NetPower_TestBed"
    bro_dnp3_parser_dir = base_dir + "/src/utils/dnp3_timing/dnp3_parser_bro/"
    bro_json_log_conf = "/home/moses/bro/scripts/policy/tuning/json-logs.bro"
    bro_cmd = "/usr/local/bro/bin/bro"

    try:
        p = DNP3PCAPPostProcessing(
            base_dir,
            bro_dnp3_parser_dir,
            bro_cmd,
            bro_json_log_conf,
         project_name)
        p.collect_data(pcap_file_name)

        if p.data:
            print "------------------------"
            print " DNP3 Latency Data:"
            print "------------------------"
            print p.data
            if (p.data[5:]): # print stats if there are more than 5 samples
                print "Num samples:", len(p.data[5:])
                print "mean:", numpy.mean(p.data[5:])
                print "std:", numpy.std(p.data[5:])
                print "min:", min(p.data[5:])
                print "max:", max(p.data[5:])

        if p.periodicity_data:
            print "------------------------"
            print " DNP3 Periodicity Data:"
            print "------------------------"
            print p.periodicity_data
            if (p.periodicity_data[5:]): # print stats if there are more than 5 samples
                print "Num samples:", len(p.periodicity_data[5:])
                print "mean:", numpy.mean(p.periodicity_data[5:])
                print "std:", numpy.std(p.periodicity_data[5:])
                print "min:", min(p.periodicity_data[5:])
                print "max:", max(p.periodicity_data[5:])
            print "------------------------"

    except:
        print "No DNP3 packets were transmitted ..."


def main():

    run_time = 15
    root_user_name = "moses"
    root_password = "passwd"

    emulated_flow_definitions = {
        'dnp3': [
            ('h1', 'h2', 'h3', 'h4', 'h5'), ('h1', 'h2', 'h3', 'h4', 'h5')], 'ping': [
            ('h1', 'h6', 'h7'), ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')], 'http': [
                ('h1', 'h7'), ('h1', 'h7')], 'ssh': [
                    ('h7',), ('h1',)], 'telnet': [
                        ('h1',), ('h2', 'h3', 'h4', 'h5')], 'nmap': [
                            ('h1', 'h6', 'h7'), ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')]}

    background_flows = ['ssh', 'telnet', 'http', 'ping']
    scans = ['nmap']
    control_flows = ['dnp3']

    script_dir = os.path.dirname(os.path.realpath(__file__))
    idx = script_dir.index('NetPower_TestBed')
    base_dir = script_dir[0:idx] + "NetPower_TestBed"
    replay_pcaps_dir = script_dir + "/attack_plan"

    network_configuration = get_network_configuration()
    log_dir = base_dir + "/logs/" + str(network_configuration.project_name)
    mn_h1 = network_configuration.mininet_obj.get("h1")
    mn_h2 = network_configuration.mininet_obj.get("h2")
    mn_h3 = network_configuration.mininet_obj.get("h3")

    bg_flows = [

        # Ping 1->2
        EmulatedTrafficFlow(type=TRAFFIC_FLOW_ONE_SHOT,
                            offset=1,
                            inter_flow_period=0,
                            run_time=run_time,
                            src_mn_node=network_configuration.mininet_obj.get(
                                "h1"),
                            dst_mn_node=network_configuration.mininet_obj.get(
                                "h2"),
                            root_user_name=root_user_name,
                            root_password=root_password,
                            server_process_start_cmd="",
                            client_expect_file="ping -w " + \
                            str(run_time-1) + " -i 0.2 10.0.0.2",
                            long_running=True),

        # Dnp3 1->3
        EmulatedTrafficFlow(type=TRAFFIC_FLOW_ONE_SHOT,
                            offset=1,
                            inter_flow_period=0,
                            run_time=run_time,
                            src_mn_node=network_configuration.mininet_obj.get(
                                "h1"),
                            dst_mn_node=network_configuration.mininet_obj.get(
                                "h3"),
                            root_user_name=root_user_name,
                            root_password=root_password,
                            server_process_start_cmd='python ' + base_dir + "/src/cyber_network/dnp3_slave.py --slave_ip " + \
                            network_configuration.mininet_obj.get("h3").IP() + " --life_time " + str(run_time),
                            client_expect_file='python ' + base_dir + "/src/cyber_network/dnp3_master.py --slave_ip " + \
                            network_configuration.mininet_obj.get("h3").IP() + " --life_time " + str(run_time),
                            long_running=True),

        # UDP 1->3
        EmulatedTrafficFlow(type=TRAFFIC_FLOW_ONE_SHOT,
                            offset=1,
                            inter_flow_period=0,
                            run_time=run_time,
                            src_mn_node=mn_h1,
                            dst_mn_node=mn_h3,
                            root_user_name=root_user_name,
                            root_password=root_password,
                            server_process_start_cmd='python ' + base_dir + "/src/cyber_network/simple_udp_server.py",
                            client_expect_file='python ' + base_dir + "/src/cyber_network/simple_udp_client.py",
                            long_running=True),

        # SSH 1->2
        EmulatedTrafficFlow(type=TRAFFIC_FLOW_ONE_SHOT,
                            offset=1,
                            inter_flow_period=0,
                            run_time=run_time,
                            src_mn_node=network_configuration.mininet_obj.get(
                                "h1"),
                            dst_mn_node=network_configuration.mininet_obj.get(
                                "h2"),
                            root_user_name=root_user_name,
                            root_password=root_password,
                            server_process_start_cmd="/usr/sbin/sshd -D -p 22 -o ListenAddress=" + \
                            network_configuration.mininet_obj.get("h2").IP(),
                            client_expect_file='python ' + base_dir + "/src/cyber_network/ssh_session.py --dest_ip " + \
                            mn_h2.IP() + " --username " + root_user_name + " --password " + root_password,
                            long_running=True),

        # Telnet 1->2
        EmulatedTrafficFlow(type=TRAFFIC_FLOW_ONE_SHOT,
                            offset=1,
                            inter_flow_period=0,
                            run_time=run_time,
                            src_mn_node=network_configuration.mininet_obj.get(
                                "h1"),
                            dst_mn_node=network_configuration.mininet_obj.get(
                                "h2"),
                            root_user_name=root_user_name,
                            root_password=root_password,
                            server_process_start_cmd="sudo socat tcp-l:23,reuseaddr,fork exec:/bin/login,pty,setsid,setpgid,stderr,ctty",
                            client_expect_file='python ' + base_dir + "/src/cyber_network/telnet_session.py --dest_ip " + mn_h2.IP(),
                            long_running=True),
    ]

    exp = TimeKeeperIntegration(run_time,
                                network_configuration,
                                script_dir,
                                base_dir,
                                replay_pcaps_dir,
                                log_dir,
                                bg_flows,
                                [],
                                [])

    exp.start_project()
    measure_dnp3_latencies(exp.project_name, "s1-eth2-s2-eth2.pcap")
    os.system("sudo killalll -9 python")
    os.system("sudo killall -9 sudo")


if __name__ == "__main__":
    main()

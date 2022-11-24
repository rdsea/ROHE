from node import Node, Node_Jet
import time
PROMETHEUS = 'http://130.233.193.12:9090/'

rasp_01 = Node("master_rasp01", "130.233.193.12:9100", PROMETHEUS, "../metric_map/rasp_metric_map.json")
# rasp_02 = Node("worker_rasp02", "192.168.0.20:9100", PROMETHEUS, "../metric_map/rasp_metric_map.json")
# rasp_03 = Node("worker_rasp03", "192.168.0.21:9100", PROMETHEUS, "../metric_map/rasp_metric_map.json")
# rasp_04 = Node("worker_rasp04", "192.168.0.22:9100", PROMETHEUS, "../metric_map/rasp_metric_map.json")
# rasp_05 = Node("worker_rasp05", "192.168.0.23:9100", PROMETHEUS, "../metric_map/rasp_metric_map.json")


# jet_01 = Node_Jet("worker_jet01", "192.168.0.11:9100", PROMETHEUS, "../metric_map/jet_metric_map.json")
# jet_02 = Node_Jet("worker_jet02", "192.168.0.12:9100", PROMETHEUS, "../metric_map/jet_metric_map.json")
# jet_03 = Node_Jet("worker_jet03", "192.168.0.13:9100", PROMETHEUS, "../metric_map/jet_metric_map.json")
# jet_04 = Node_Jet("worker_jet04", "192.168.0.14:9100", PROMETHEUS, "../metric_map/jet_metric_map.json")

while True:
    rasp_01.get_report()
    # rasp_02.get_report()
    # rasp_03.get_report()
    # rasp_04.get_report()
    # rasp_05.get_report()
    # jet_01.get_report()
    # jet_02.get_report()
    # jet_03.get_report()
    # jet_04.get_report()
    print(rasp_01)
    # print(rasp_02)
    # print(rasp_03)
    # print(rasp_04)
    # print(rasp_05)
    # print(jet_01)
    # print(jet_02)
    # print(jet_03)
    # print(jet_04)
    time.sleep(1)
   
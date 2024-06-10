import ray

print("trying to connect to Ray!")
ray.init()
print("now executing some code with Ray!")
import time

start = time.time()


@ray.remote
def f():
    time.sleep(0.01)
    return ray._private.services.get_node_ip_address()


values = set(ray.get([f.remote() for _ in range(1000)]))
print("Ray Nodes: ", str(values))
file = open("/tmp/ray_nodes.txt", "a")
file.write("available nodes: %s\n" % str(values))
file.close()
end = time.time()
print("Execution time = ", end - start)

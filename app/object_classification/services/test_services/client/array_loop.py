import json
import argparse



if __name__ == '__main__':
    # init_env_variables()
    parser = argparse.ArgumentParser(description="Argument for choosingg model to request")
    # parser.add_argument('--test_ds', type= str, help='default test dataset path', 
    #             default= "01.jpg")
    parser.add_argument('--test_ds', type= str, help='test dataset path', 
                default= "/Users/tringuyen/workplace/Study/PhD/Github/rdsea/test_model/datasets/BDD100K-Classification/test.h5")
    parser.add_argument('--rate', type= int, help='number of requests per second', default= 20)
    parser.add_argument('--device_id', type= str, help='specify device id', default= "aaltosea_cam_01")

    # Parse the parameters
    args = parser.parse_args()
    device_id = args.device_id
    test_ds = args.test_ds
    req_rate = args.rate

    # config = {
    #     'device_id': config['device_id'],
    #     'mqtt_config': config['mqtt_config'],
    #     'test_ds': args.test_ds,
    #     'rate': args.rate,
    # }
    # main(config= config)
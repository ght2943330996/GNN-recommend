from recbole.quick_start import run_recbole

if __name__ == '__main__':
    # 加载配置文件
    config_file_list = ['./lightgcn_config.yaml']
    print("开始训练 LightGCN 模型...")
    print(f"配置文件：{config_file_list}")

    # 调用 RecBole 框架的训练函数
    run_recbole(model='LightGCN', dataset='yelp_tourism', config_file_list=config_file_list)

    print("训练完成！模型已保存。")

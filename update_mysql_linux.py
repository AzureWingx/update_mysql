# -*- coding: utf-8 -*-

import subprocess
import os
import re
import codecs
import sys
if sys.version_info[0] < 3:
    reload(sys)
    sys.setdefaultencoding('utf-8')

# 定义全局变量
HOST = "127.0.0.1"
USERNAME = "root"
PASSWORD = "password"
DB_NAME = "largescree"

try:
    # 尝试连接3306端口
    try:
        subprocess.call("mysql -h {} -P 3306 -u {} -p{} {} -e 'SHOW DATABASES' > /dev/null 2>&1".format(HOST, USERNAME, PASSWORD, DB_NAME), shell=True)
        print("成功连接3306端口")
        port = 3306
    except subprocess.CalledProcessError:
        print("无法连接3306端口，尝试连接xxx端口")
        subprocess.call("mysql -h {} -P xxx -u {} -p{} {} -e 'SHOW DATABASES' > /dev/null 2>&1".format(HOST, USERNAME, PASSWORD, DB_NAME), shell=True)
        print("成功连接xxx端口")
        port = xxx

    # 读取mysql.sql文件
    file_path = os.path.join(os.getcwd(), "mysql.sql")
    print("正在读取文件：")
    print(file_path)
    with codecs.open(file_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    # 过滤掉以"--"开头的句子
    sql_script = re.sub(r'^.*--.*$', '', sql_script, flags=re.MULTILINE)

    print("成功读取文件")

    # 使用正则表达式匹配创建表的语句
    create_table_queries = re.findall(r'CREATE TABLE `(.+?)` \((.+?);', sql_script, re.DOTALL)
    
    # 获取本地数据库中已存在的表及其结构
    result = subprocess.check_output("mysql -h {} -P {} -u {} -p{} {} -e 'SHOW TABLES'".format(HOST, port, USERNAME, PASSWORD, DB_NAME), shell=True).decode('utf-8')
    local_tables = result.strip().split("\n")[1:]

    # 检查表名是否符合命名规范
    valid_tables = [table for table in local_tables if re.match(r'^[a-zA-Z0-9_]+$', table)]

    for query in create_table_queries:
        table_name = query[0]
        if table_name not in valid_tables:
            print("表" + table_name + "不符合命名规范，将被忽略")
            continue
        table_structure = query[1]

        match = re.search(r'^(.*?)(?:PRIMARY KEY|\) ENGINE)', table_structure, re.DOTALL)
        if match:
            table_structure_trimmed = match.group(1)
        else:
            print("未找到匹配的内容")

        show_columns_command = "mysql -h {} -P {} -u {} -p{} {} -e 'SHOW COLUMNS FROM {}'".format(HOST, port, USERNAME, PASSWORD, DB_NAME, table_name)
        result = subprocess.check_output(show_columns_command, shell=True).decode('utf-8')
        local_columns = result.strip().split("\n")[1:]
        column_info = {column.split("\t")[0]: column.split("\t")[1] for column in local_columns}

        field_definitions = re.findall(r'`([^`]+)`\s*([^,]+)', table_structure_trimmed)
        for field_definition in field_definitions:
            field_name = field_definition[0]
            field_type = field_definition[1]
            field_type = field_type.replace("'", '"')
            field_type0 = field_type.split(' ')[0]
            if field_name == "describe":
                print("字段名" + field_name + "是 MySQL 的保留关键字，将跳过处理")
                continue
            if 'decimal' in field_type0:
                print("字段类型中包含'decimal'关键字，将跳过处理")
                continue
            if field_name not in column_info:
                print("表" + table_name + "中字段{}不存在，将新增字段".format(field_name))
                alter_query = "mysql -h {} -P {} -u {} -p{} {} -e 'ALTER TABLE {} ADD COLUMN {} {};'".format(HOST, port, USERNAME, PASSWORD, DB_NAME, table_name, field_name, field_type)
                subprocess.call(alter_query, shell=True)
            elif column_info[field_name] != field_type0:
                print("表" + table_name + "中字段{}类型不匹配，当前类型为{}，将变更字段类型为{}".format(field_name, column_info[field_name], field_type0))
                alter_query = "mysql -h {} -P {} -u {} -p{} {} -e 'ALTER TABLE {} MODIFY COLUMN {} {};'".format(HOST, port, USERNAME, PASSWORD, DB_NAME, table_name, field_name, field_type)
                subprocess.call(alter_query, shell=True)

        print("表" + table_name + "已检查")

    print("更新完成")

except Exception as e:
    print("发生错误：", e)
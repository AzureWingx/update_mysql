# -*- coding: utf-8 -*-

import pymysql
import os
import re

try:
    # 尝试连接3306端口
    try:
        local_db = pymysql.connect(
          host="127.0.0.1",
          port=3306,
          user="root",
          password="password",
          database="test"
        )
    except pymysql.Error as e:
        print("无法连接3306端口，尝试连接xxx端口")
        local_db = pymysql.connect(
          host="127.0.0.1",
          port=xxx,
          user="root",
          password="password",
          database="test"
        )

    # 读取ads.sql文件
    file_path = os.path.join(os.getcwd(), "ads.sql")
    print("正在读取文件：", file_path)
    with open(file_path, "r", encoding='utf-8') as f:
        sql_script = f.read()
    
    # 过滤掉以"--"开头的句子
    sql_script = re.sub(r'--.*', '', sql_script)

    print("成功读取文件")

    # 使用正则表达式匹配创建表的语句
    create_table_queries = re.findall(r'CREATE TABLE IF NOT EXISTS `(.+?)` \((.+?)\);', sql_script, re.DOTALL)
    print(create_table_queries)

    # 获取本地数据库中已存在的表及其结构
    local_cursor = local_db.cursor()
    local_cursor.execute("SHOW TABLES")
    local_tables = [table[0] for table in local_cursor.fetchall()]
    # print("本地数据库中已存在的表：", local_tables)

    # 检查表名是否符合命名规范
    valid_tables = [table for table in local_tables if re.match(r'^[a-zA-Z0-9_]+$', table)]
    # print("经过命名规范检查后的表：", valid_tables)

    for query in create_table_queries:
        table_name = query[0]
        if table_name not in valid_tables:
            print("表" + table_name + "不符合命名规范，将被忽略")
            continue
        table_structure = query[1]
        
        # 使用正则表达式匹配第一个分号前的内容
        match = re.search(r'^(.*?)(?:PRIMARY KEY|\) ENGINE)', table_structure, re.DOTALL)
        if match:
          table_structure_trimmed = match.group(1)
        else:
          print("未找到匹配的内容")
        
        local_cursor.execute("SHOW COLUMNS FROM {}".format(table_name))
        local_columns = local_cursor.fetchall()
        column_info = {column[0]: column[1] for column in local_columns}

        
        field_definitions = re.findall(r'`([^`]+)`\s*([^,]+)',table_structure_trimmed)
        for field_definition in field_definitions:
              field_name = field_definition[0]
              field_type = field_definition[1]
              field_type0 = field_type.split(' ')[0]
              if field_name == "describe":  # 检查字段名是否为保留关键字
                print("字段名" + field_name + "是 MySQL 的保留关键字，将跳过处理")
                continue
              if re.match(r'^(int|bigint)\(\d+\)$', field_type0):
                field_type0 = re.sub(r'\(\d+\)', '', field_type0)
              if field_name not in column_info:
                print("表" + table_name + "中字段{field_name}不存在，将新增字段")
                alter_query = "ALTER TABLE {} ADD COLUMN {} {};".format(table_name, field_name, field_type)
                # print("生成的SQL语句：", alter_query)  # 打印生成的SQL语句
                local_cursor.execute(alter_query)
              elif column_info[field_name] != field_type0:
                print("表" + table_name + "中字段{field_name}类型不匹配，当前类型为" + column_info[field_name] + "，将变更字段类型为" + field_type0)
                alter_query = "ALTER TABLE {} MODIFY COLUMN {} {};".format(table_name, field_name, field_type)
                # print("生成的SQL语句：", alter_query)  # 打印生成的SQL语句
                local_cursor.execute(alter_query)

        print("表" + table_name + "已检查")

    # 提交更改
    local_db.commit()

    # 关闭连接
    local_cursor.close()
    local_db.close()

    print("更新完成")

except Exception as e:
    print("发生错误：", e)
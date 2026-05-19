# agent定义

将以下需求，转换为一个专业做研究，轮动，收敛到文档中的agent：design_research

# 文件夹需求

每次根据用户输入文件，创建任务目录，并在任务目录下，创建

1.planning ：作为aI planning的输出

2.research：ai根据需求，使用web_search_tavily skill到国内外网站上找到各种相关的材料；

3.working：整理材料，生成中间中间分析.md；自动带上时间戳；

4.result: 我确认后将输出结果保存到result下，并且每次带上时间戳；

result使用html_chip_design_spec skill生成html格式的result，其中将调用drawio_chip_diagram skill生成图片

同时 result里面支持各种md文件；

# sub-agent需求

design_research.planning : 根据需求给出实现方案，写出./1.planning/planning.yml文件，输出文件放入./1.planning 目录; 同时，将各种输入文件解析之后，写入./1.planning；根据需求，先给出第一轮推荐的搜索地址，比如mcp/github/skillhub/ieee 论文地址；

    ./1.planning/planning.yml中包括agent迭代次数，默认为5轮；可以由用户更改；

design_research.research: 使用各种不同的软件/协议/爬虫方式，到推荐出来的地址里面去搜索数据，并将原始文件内容转换为md格式，写入./2.research; 其中md文件需要保留图片，表格等；

design_research.working：分析research的数据，提取关键结果，写出阶段性报告；判断是否需要补充新的research方向，如果需要，给出新的推荐地址和关键词；之后回到research状态；

    此轮回，迭代次数由./1.planning/planning.yml决定；

design_research.workingresult:生词报告结果；working agent迭代结束后，整体按照需求输出html和md格式的分析报告，以及参加脚本；注意md文件中需要带有

# agent文档

使用html_chip_design_spec skill生成design_research agent的详细设计规格：./agents/design_research.spec.html，和一个简单的使用指导user_guide: ./agents/design_research.userguide.html

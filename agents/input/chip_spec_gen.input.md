# agent定义

将以下需求，转换为一个专业做写芯片设计文档的专业agent，chip_spec_gen
agent保存所在路径在: ./agents/commands/

# 文件夹需求

每次根据用户输入文件，创建任务目录，并在任务目录下，创建

1.planning ：阅读输入文件，和用户要求，规划后续工作，输出文件作为AI planning的输出;

2.slice：ai根据需求，将输入文档材料，按照章节将文章提取为md，图片提取问图片，标签后放入2.slice；

3.working：根据输出文件要求，结合2.slice中的材料，从新整理需要哪些章节，章节需求；从新按照输出章节要求，排列文字和图片；检查是否输出文件中的所有章节都有对应的文字和图表，如果没有继续到2.slice中寻找。如果找不到合适的文字描述，将对应内容标识为：待补充；如果能找到，轻度润色文字；

4.result: 我确认后将输出结果保存到result下，并且每次带上时间戳；

result使用html_chip_design_spec skill生成html格式的result，其中将调用drawio_chip_diagram skill生成图片

同时 result里面支持各种md文件；

# sub-agent需求

chip_spec_gen.planning : 根据输入文件格式，转换文档为md；并给出实现方案，写出./1.planning/planning.yml文件，输出文件放入./1.planning 目录; 同时，将各种输入文件解析之后，写入./1.planning；

    ./1.planning/planning.yml中包括agent迭代次数，默认为5轮；可以由用户更改；

chip_spec_gen.slice： 按照输入文件章节和图片，原始文件内容和图片转换为md格式，写入./2.slice; 其中md文件需要保留图片，表格等；

chip_spec_gen.working：分析slice的数据，提取关键结果，根据需求选择合适的skill，生成输出文件的目录下对应的文字和图片，表格等；

写出阶段性报告；判断是否有章节缺少内容描述，如果需要，回到slice中去寻找更多的相关材料；

    此轮回，迭代次数由./1.planning/planning.yml决定；

design_research.workingresult:生词报告结果；working agent迭代结束后，整体按照需求输出html和格式的分析报告，以及参加脚本；注意md文件中需要带有图片；

# agent文档

使用html_chip_design_spec skill生成此agent的详细设计规格：./agents/chip_spec_gen.spec.html，和一个简单的使用指导user_guide: ./agents/chip_spec_gens.userguide.html

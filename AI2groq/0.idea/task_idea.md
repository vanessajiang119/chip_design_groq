我想用3天时间，完成一个groq芯片 文档设计/rtl设计/软件开发/编译器设计/跑通一个小的transformer算子；


使用design_research agenti，帮我想去收集所有的groq芯片的设计文档，ieee论文，开源项目；然后做出具体执行plan

架构分析内容至少包括：

1. 架构分析，
2. 关键参数分析；
3. 详细设计结构
4. 3天实现的开发计划；

每一个话题都按照需求，自动使用design_research agenti向下扩展两层，最后将所有的结果，汇总到最上层，以一个output结果输出

启动递归 agent 继续进行架构分析和详细设计分析

其中，架构分析材料中，将2.research和3.working；4.result的中间markdown文件，都转换为html格式，作为架构分析的参考材料，包含到最终形成的架构分析报告中；

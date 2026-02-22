# IndexTTS2 Bug Finder：已发现样本汇总

- 更新时间: 2026-02-22 17:46:30
- 链路: IndexTTS2 TTS -> Whisper ASR (GPU, `large-v3-turbo.pt`) -> 规则评分(CER/WER/critical) -> `kimi` 语义等价/新颖性过滤 -> SQLite/报告
- 说明: 这里的 “ASR” 是 Whisper 转写结果；同音字/繁简体差异在中文里本来就常见，筛选时已尽量用 `kimi` 排除语义等价的样本。

## 运行产物
- `artifacts_indextts2_guwen_poly1`: accepted_lines=13 | report=`artifacts_indextts2_guwen_poly1/report.html` | db=`artifacts_indextts2_guwen_poly1/bugs.sqlite` | export=`artifacts_indextts2_guwen_poly1/accepted.jsonl`
- `artifacts_indextts2_live3w`: accepted_lines=23 | report=`artifacts_indextts2_live3w/report.html` | db=`artifacts_indextts2_live3w/bugs.sqlite` | export=`artifacts_indextts2_live3w/accepted.jsonl`
- `artifacts_indextts2_target1`: accepted_lines=10 | report=`artifacts_indextts2_target1/report.html` | db=`artifacts_indextts2_target1/bugs.sqlite` | export=`artifacts_indextts2_target1/accepted.jsonl`
- `artifacts_indextts2_try2`: accepted_lines=2 | report=`artifacts_indextts2_try2/report.html` | db=`artifacts_indextts2_try2/bugs.sqlite` | export=`artifacts_indextts2_try2/accepted.jsonl`

## 统计（去重到 ref_text）
- accepted_lines 总数: 48
- unique_ref_text: 43
- 主题分布:
  - 古文与多音字: 13
  - 数字与格式: 18
  - 中英混合与代码 Token: 10
  - 标点与符号: 2

## 样本列表（按主题，ref_text 去重）
### 古文与多音字 (13)
1. score=50.5 cer=0.75 crit=0.00 tags=guwen,polyphone
GT: 重为轻根，静为躁君。
ASR: 崇为清甘 敬为造军
subs: 轻根静->清甘敬; 躁君->造军; 重->崇
src: artifacts_indextts2_guwen_poly1 id=a13c7b9d-ad8a-4b6b-91fa-2fc60f5a0bab score=50.5 audio=artifacts_indextts2_guwen_poly1/audio/a13c7b9d-ad8a-4b6b-91fa-2fc60f5a0bab.wav

2. score=49.0 cer=0.30 crit=1.00 tags=guwen,negation,polyphone
GT: 曾子曰：吾日三省吾身。
ASR: 曾子曰 无日三省无身
subs: 吾->无
src: artifacts_indextts2_guwen_poly1 id=d74343f8-d76b-4d7b-bc31-8b5631d3de34 score=49.0 audio=artifacts_indextts2_guwen_poly1/audio/d74343f8-d76b-4d7b-bc31-8b5631d3de34.wav

3. score=47.5 cer=0.62 crit=0.00 tags=guwen,polyphone
GT: 度德量力，量力而行。
ASR: 杜德亮丽 亮丽而行
subs: 量力量力->亮丽亮丽; 度->杜
src: artifacts_indextts2_guwen_poly1 id=87069126-5db0-438c-991b-663d735f2547 score=47.5 audio=artifacts_indextts2_guwen_poly1/audio/87069126-5db0-438c-991b-663d735f2547.wav

4. score=44.5 cer=0.21 crit=1.00 tags=negation,polyphone
GT: 老师说：好好学习，不要好高骛远。
ASR: 老师说好好学习 不要好高无援
subs: 骛远->无援
src: artifacts_indextts2_guwen_poly1 id=35a84f44-a6ba-46e4-b9f5-a182eea79b55 score=44.5 audio=artifacts_indextts2_guwen_poly1/audio/35a84f44-a6ba-46e4-b9f5-a182eea79b55.wav

5. score=40.7 cer=0.14 crit=1.00 tags=guwen,negation,polyphone
GT: 问渠那得清如许，为有源头活水来。
ASR: 问渠纳得清如许 未有源头活水来
subs: 为->未; 那->纳
src: artifacts_indextts2_guwen_poly1 id=cfcda637-e8ec-4213-86ad-6f4e7f77530e score=40.7 audio=artifacts_indextts2_guwen_poly1/audio/cfcda637-e8ec-4213-86ad-6f4e7f77530e.wav

6. score=40.2 cer=0.41 crit=0.33 tags=guwen,numbers,polyphone
GT: 冠者五六人，童子六七人，浴乎沂，风乎舞雩。
ASR: 冠者五六人 童子六七人 御护仪 奉护五欲
subs: 浴乎沂风乎舞雩->御护仪奉护五欲
src: artifacts_indextts2_guwen_poly1 id=614caedf-c6f1-4d4c-88ab-b592232df243 score=40.2 audio=artifacts_indextts2_guwen_poly1/audio/614caedf-c6f1-4d4c-88ab-b592232df243.wav

7. score=28.0 cer=0.38 crit=0.00 tags=guwen,polyphone
GT: 将军将至，士卒皆惊。
ASR: 将军将至 士族接近
subs: 卒皆惊->族接近
src: artifacts_indextts2_guwen_poly1 id=649497b7-58d2-4bf7-b68d-783684f5f7f1 score=28.0 audio=artifacts_indextts2_guwen_poly1/audio/649497b7-58d2-4bf7-b68d-783684f5f7f1.wav

8. score=28.0 cer=0.38 crit=0.00 tags=guwen,polyphone
GT: 礼乐崩坏，刑罚不中。
ASR: 李月崩壞刑罚不中
subs: 礼乐->李月; 坏->壞
src: artifacts_indextts2_guwen_poly1 id=a6134318-9b6d-4db8-8540-137349227931 score=28.0 audio=artifacts_indextts2_guwen_poly1/audio/a6134318-9b6d-4db8-8540-137349227931.wav

9. score=25.5 cer=0.33 crit=0.00 tags=guwen,polyphone
GT: 学而时习之，不亦说乎？
ASR: 雪儿实习之不亦说乎
subs: 学而时->雪儿实
src: artifacts_indextts2_guwen_poly1 id=9d2589cf-e5f8-49bf-bf1e-2006ae4587aa score=25.5 audio=artifacts_indextts2_guwen_poly1/audio/9d2589cf-e5f8-49bf-bf1e-2006ae4587aa.wav

10. score=25.5 cer=0.33 crit=0.00 tags=guwen,polyphone
GT: 长者赐，不敢辞。
ASR: 长者刺不敢刺
subs: 赐->刺; 辞->刺
src: artifacts_indextts2_guwen_poly1 id=786dfab1-01b1-4f4c-abae-24f4a1d9f75d score=25.5 audio=artifacts_indextts2_guwen_poly1/audio/786dfab1-01b1-4f4c-abae-24f4a1d9f75d.wav

11. score=24.0 cer=0.31 crit=0.00 tags=guwen,polyphone
GT: 数罟不入洿池，鱼鳖不可胜食也。
ASR: 属虚不入戏池 鱼鞭不可胜食也
subs: 数罟->属虚; 洿->戏; 鳖->鞭
src: artifacts_indextts2_guwen_poly1 id=28af01b2-a928-409b-8d8e-8e990d09f3a5 score=24.0 audio=artifacts_indextts2_guwen_poly1/audio/28af01b2-a928-409b-8d8e-8e990d09f3a5.wav

12. score=20.5 cer=0.25 crit=0.00 tags=guwen,polyphone
GT: 知之者不如好之者，好之者不如乐之者。
ASR: 支持者不如耗之者 耗之者不如乐之者
subs: 知之->支持; 好->耗
src: artifacts_indextts2_guwen_poly1 id=622cf758-90fa-4552-a430-daad5ead6c37 score=20.5 audio=artifacts_indextts2_guwen_poly1/audio/622cf758-90fa-4552-a430-daad5ead6c37.wav

13. score=18.0 cer=0.25 crit=0.00 tags=guwen,polyphone,punctuation
GT: 礼乐崩坏，刑罚不中。（括号里也要读出来）
ASR: 李月崩壞刑罚不中 括号你也要读出来
subs: 礼乐->李月; 坏->壞; 里->你
src: artifacts_indextts2_guwen_poly1 id=d5c67e4b-8a08-4ae0-bb9a-75fb0b9cfec9 score=18.0 audio=artifacts_indextts2_guwen_poly1/audio/d5c67e4b-8a08-4ae0-bb9a-75fb0b9cfec9.wav

### 数字与格式 (18)
14. score=83.3 cer=1.15 crit=0.67 tags=broadcast,mixed_lang,numbers
GT: 本月目标：转化率 ≥ 12.5%，退款率 ≤ 1.2%。
ASR: 本月目标 转化率大于等于百分之十二点五 推款率小于等于百分之一点二
subs: 12.5%退->之十二点五推; 1.2%->之一点二
src: artifacts_indextts2_live3w id=1630d78f-4c5b-4b58-af64-0dddbd19f133 score=83.3 audio=artifacts_indextts2_live3w/audio/1630d78f-4c5b-4b58-af64-0dddbd19f133.wav

15. score=77.5 cer=0.78 crit=1.00 tags=broadcast,mixed_lang,numbers
GT: 请核对金额：¥1,234,567.89，若有误请立即反馈。
ASR: 请核对金额一元二十三万四千五百六十七点八九 若有务情立即反馈
subs: 1234567.89->四千五百六十七点八九; 误请->务情
src: artifacts_indextts2_live3w id=ae4552a1-491b-4e7c-a922-2026cdbd1c2c score=77.5 audio=artifacts_indextts2_live3w/audio/ae4552a1-491b-4e7c-a922-2026cdbd1c2c.wav; artifacts_indextts2_target1 id=96fd6484-eb28-4600-b4dd-13a9bebe7c0e score=77.2 audio=artifacts_indextts2_target1/audio/96fd6484-eb28-4600-b4dd-13a9bebe7c0e.wav

16. score=73.1 cer=0.71 crit=1.00 tags=mixed_lang,numbers
GT: 请在 config.yaml 里把 timeout 设置为 30s，再重启。
ASR: 请再坑费个 燕猫里把胎猫的设置为三十秒 再重启
subs: g.yaml->再坑费个燕猫; 30s->三十秒; out->胎猫的
src: artifacts_indextts2_live3w id=8d13a6a3-f570-4688-a6fe-a01afd85cf46 score=73.1 audio=artifacts_indextts2_live3w/audio/8d13a6a3-f570-4688-a6fe-a01afd85cf46.wav

17. score=70.9 cer=0.78 crit=0.75 tags=broadcast,mixed_lang,numbers
GT: 请把 2^10 读成 1024，不要读成 210。
ASR: 请把二十独成一千零二十四 不要独成二一零
subs: 210读成1024->十独成一千零二十四; 210->二一零; 读->独
src: artifacts_indextts2_live3w id=bc9a4be8-45fb-49bb-a7d3-80ba675e4f7c score=70.9 audio=artifacts_indextts2_live3w/audio/bc9a4be8-45fb-49bb-a7d3-80ba675e4f7c.wav

18. score=67.0 cer=0.69 crit=0.75 tags=mixed_lang,numbers,punctuation
GT: 如果你看到“404/500/502”，别慌：先刷新，再清缓存。
ASR: 如果你看到五十分之四百零四 五百零二分之零 别晃 先刷新 再轻缓存
subs: 404/500/502别慌:->之四百零四五百零二分之零别晃; 清->轻
src: artifacts_indextts2_live3w id=c755cee1-9e76-41b1-9067-29c44492ba05 score=67.0 audio=artifacts_indextts2_live3w/audio/c755cee1-9e76-41b1-9067-29c44492ba05.wav

19. score=64.8 cer=0.64 crit=0.80 tags=broadcast,mixed_lang,numbers
GT: 账单号：INV-2026-000123，开票日期 2026-02-01。
ASR: 账单号因为两千零二十六 零零零一二三 开票日期2026年2月1日
subs: NV-2026-000123->因为两千零二十六零零零一二三; -01->月1日; 0->年
src: artifacts_indextts2_try2 id=2bb357d3-2f12-459a-9aac-8edd1825d091 score=64.8 audio=artifacts_indextts2_try2/audio/2bb357d3-2f12-459a-9aac-8edd1825d091.wav; artifacts_indextts2_live3w id=a7514f96-8d54-42d1-bf17-cbdd79a2fb60 score=50.5 audio=artifacts_indextts2_live3w/audio/a7514f96-8d54-42d1-bf17-cbdd79a2fb60.wav

20. score=61.8 cer=0.58 crit=0.86 tags=broadcast,mixed_lang,numbers
GT: 航班 CA1234 于 08:20 起飞，预计 10:05 到达，延误 15 分钟。
ASR: 航班 擦二三四 于八点二十分起飞 预计十点零五分到达 延误十五分钟
subs: 08:20->八点二十分; 10:05->十点零五分; 1234->擦二三四
src: artifacts_indextts2_live3w id=0457a42d-566c-4ec0-8e2f-4ccacb84d5c8 score=61.8 audio=artifacts_indextts2_live3w/audio/0457a42d-566c-4ec0-8e2f-4ccacb84d5c8.wav

21. score=59.9 cer=0.46 crit=1.00 tags=mixed_lang,numbers
GT: 文件名为 report_2026-02-20_FINAL_v3.pdf，请确认版本。
ASR: 文件名为Report T 2026年2月20日 成Final PDF 请确认版本
subs: NAL_v3.pdf->日成FinalPDF; -->月; 0->年
src: artifacts_indextts2_live3w id=472e37b9-c7f7-4f40-8144-edd9818ef291 score=59.9 audio=artifacts_indextts2_live3w/audio/472e37b9-c7f7-4f40-8144-edd9818ef291.wav; artifacts_indextts2_target1 id=350dfc8f-261a-4c53-aa5c-ce4f33d5b81c score=57.8 audio=artifacts_indextts2_target1/audio/350dfc8f-261a-4c53-aa5c-ce4f33d5b81c.wav

22. score=56.6 cer=0.43 crit=1.00 tags=broadcast,mixed_lang,numbers
GT: 阈值为 1e-3，采样率 44.1 kHz，帧长 25 ms。
ASR: 预值为113 采样率44.1K核子 正常25毫秒
subs: kHz帧长->K核子正常; ms->毫秒; -->1
src: artifacts_indextts2_live3w id=8ee129da-7270-4e12-9c75-9a8e4fccc136 score=56.6 audio=artifacts_indextts2_live3w/audio/8ee129da-7270-4e12-9c75-9a8e4fccc136.wav

23. score=52.7 cer=0.35 crit=1.00 tags=numbers,unicode
GT: 请逐字朗读：a​b​c（每个字母之间有零宽空格）。
ASR: 请竹子朗读ABC 每个字母之间有灵宽空格
subs: abc->ABC; 逐字->竹子; 零->灵
src: artifacts_indextts2_live3w id=2a33b61a-c2c7-4815-a19c-0e109499d861 score=52.7 audio=artifacts_indextts2_live3w/audio/2a33b61a-c2c7-4815-a19c-0e109499d861.wav

24. score=52.2 cer=0.50 crit=0.67 tags=broadcast,mixed_lang,numbers
GT: 电池容量 5000mAh，充电功率 67W，约 0.8 小时充满。
ASR: 电池容量五千米 充电功率六十七W 约零点八小时充满
subs: 0.8->零点八; mAh->五千米; 67->十七
src: artifacts_indextts2_live3w id=ebdfc3b1-f1b3-4148-8148-b138cbfd6841 score=52.2 audio=artifacts_indextts2_live3w/audio/ebdfc3b1-f1b3-4148-8148-b138cbfd6841.wav

25. score=51.7 cer=0.33 crit=1.00 tags=mixed_lang,numbers,unicode
GT: 提示：别把 𝟙𝟚𝟛（数学粗体数字）当成普通 123。
ASR: 提示 别把数学粗体数字 当成普通一二三
subs: 123->一二三
src: artifacts_indextts2_live3w id=e7feed57-574b-47e8-849a-a770f370eae6 score=51.7 audio=artifacts_indextts2_live3w/audio/e7feed57-574b-47e8-849a-a770f370eae6.wav

26. score=46.8 cer=0.48 crit=0.50 tags=broadcast,mixed_lang,numbers
GT: 保修期 24 个月，或行驶里程 60,000 km，以先到者为准。
ASR: 保修期二十四个月 或行驶里程六十零零零公里 以仙道者为准
subs: 60000km->六十零零零公里; 24->十四; 先到->仙道
src: artifacts_indextts2_target1 id=06f8ae40-d749-45ce-96e3-363567e19ff2 score=46.8 audio=artifacts_indextts2_target1/audio/06f8ae40-d749-45ce-96e3-363567e19ff2.wav

27. score=45.5 cer=0.33 crit=0.80 tags=broadcast,mixed_lang,numbers
GT: IP 为 192.168.0.1，端口 8080；超时 30s 后重试 3 次。
ASR: IP为192.168.0.1 端口八千零八十 超时三十秒后重施三次
subs: 8080->千零八十; 30s->三十秒; 试3->施三
src: artifacts_indextts2_target1 id=f2052a62-545e-4721-81a2-69cbe1ac5bb8 score=45.5 audio=artifacts_indextts2_target1/audio/f2052a62-545e-4721-81a2-69cbe1ac5bb8.wav

28. score=41.3 cer=0.18 crit=1.00 tags=mixed_lang,numbers
GT: 我们在 Kubernetes 上跑服务，namespace 是 prod，pod 数量是 12。
ASR: 我们在Kubernetes上跑福 Namespace是Pod Pod的数量是12
subs: 务n->福N; p->P; r->P
src: artifacts_indextts2_live3w id=8037a6a3-cf0a-4b38-ac48-40ad9751c364 score=41.3 audio=artifacts_indextts2_live3w/audio/8037a6a3-cf0a-4b38-ac48-40ad9751c364.wav

29. score=38.2 cer=0.13 crit=1.00 tags=mixed_lang,numbers
GT: 邮件标题写 RE: Incident #12345，不要写成 Reply。
ASR: 邮件标题写Reincident 卓12345 不要写成Reply
subs: :I->ei; #->卓
src: artifacts_indextts2_target1 id=6186dc08-a811-4eb4-a01e-fd2db5e410d5 score=38.2 audio=artifacts_indextts2_target1/audio/6186dc08-a811-4eb4-a01e-fd2db5e410d5.wav

30. score=35.5 cer=0.50 crit=0.00 tags=broadcast,mixed_lang,numbers
GT: 每日用量 3–5 次/天，每次 0.5 ml，连续 7 天。
ASR: 每日用量三排五次 债天每次零点五毫升连续七天
subs: 0.5ml->零点五毫升; 35->排五; /->债
src: artifacts_indextts2_target1 id=c859298a-4c1c-4536-992e-8e26f1ea334d score=35.5 audio=artifacts_indextts2_target1/audio/c859298a-4c1c-4536-992e-8e26f1ea334d.wav

31. score=29.9 cer=0.13 crit=0.67 tags=mixed_lang,numbers
GT: 请把 DNS 解析指向 1.1.1.1 和 8.8.8.8，再测试 ping。
ASR: 请把DNS解析指向1.1.1.1和8.8.8.8再测试PIN
subs: ing->PIN
src: artifacts_indextts2_target1 id=e4e01985-9f26-48dc-90e7-988051d454b9 score=29.9 audio=artifacts_indextts2_target1/audio/e4e01985-9f26-48dc-90e7-988051d454b9.wav

### 中英混合与代码 Token (10)
32. score=80.0 cer=1.00 crit=0.40 tags=mixed_lang
GT: 把参数写成 `--max-retry=3`，不要写成 `--maxretry=3`。
ASR: 把参数写成B-C-Max-Ray-Tray等于三神 不要写成B-C-Max-Ray-Tray等于三
subs: ret->y-T; =3->三神; =3->于三
src: artifacts_indextts2_live3w id=fe904a50-2851-4bb7-8888-a98520c90c83 score=80.0 audio=artifacts_indextts2_live3w/audio/fe904a50-2851-4bb7-8888-a98520c90c83.wav; artifacts_indextts2_try2 id=2654301b-8a08-4bc6-8124-0ac968fa1a39 score=77.0 audio=artifacts_indextts2_try2/audio/2654301b-8a08-4bc6-8124-0ac968fa1a39.wav; artifacts_indextts2_target1 id=4db08361-f77d-41bc-8222-ed3fd7b464de score=66.0 audio=artifacts_indextts2_target1/audio/4db08361-f77d-41bc-8222-ed3fd7b464de.wav

33. score=74.3 cer=0.00 crit=0.33 tags=mixed_lang
GT: 订单状态是 `PAID`，但 webhook 没收到 event=payment.succeeded。
ASR: 订单状态是败配 但webhook没收到event 等于payment succeeded
subs: PAID`,但webhook没收到event=payment.succeeded->订单状态是败配但webhook没收到event等于paymentsucceeded
src: artifacts_indextts2_live3w id=a90c1ec0-a38b-4ac1-8bfa-a879fda7c9c2 score=74.3 audio=artifacts_indextts2_live3w/audio/a90c1ec0-a38b-4ac1-8bfa-a879fda7c9c2.wav

34. score=58.9 cer=0.44 crit=1.00 tags=mixed_lang,negation,unicode
GT: 地址写作：No. 12，别把空格吞掉。
ASR: 地址协作弄十二 别把空格吞掉
subs: .12->弄十二; 写->协
src: artifacts_indextts2_live3w id=d0576e9a-12e3-4a81-9375-f7bcd006949c score=58.9 audio=artifacts_indextts2_live3w/audio/d0576e9a-12e3-4a81-9375-f7bcd006949c.wav

35. score=48.1 cer=0.48 crit=0.47 tags=mixed_lang,unicode
GT: 这行代码看起来像 payload，但其实是 pаyload（a 是西里尔字母）。
ASR: 这行代码看起来像佩露的 但其实是PY露的 是希里尔字母
subs: oada->PY露的; oad->佩露的; 西->希
src: artifacts_indextts2_live3w id=d1be7151-9328-4124-958b-969bc827b613 score=48.1 audio=artifacts_indextts2_live3w/audio/d1be7151-9328-4124-958b-969bc827b613.wav

36. score=45.9 cer=0.46 crit=0.50 tags=mixed_lang
GT: 请把 'cache miss' 翻译成中文时不要丢掉 miss 的含义。
ASR: 请把凯史密斯翻译成中文时 不要丢掉密斯的含义
subs: miss->凯史密斯; ss->密斯
src: artifacts_indextts2_target1 id=75a696da-7107-413e-a8a8-f2514f4916b5 score=45.9 audio=artifacts_indextts2_target1/audio/75a696da-7107-413e-a8a8-f2514f4916b5.wav

37. score=39.6 cer=0.45 crit=0.27 tags=mixed_lang,unicode
GT: 注意：'＠' 是全角 at，不是 '@'。
ASR: 注意!是全杰AT,不是!
subs: 角at->杰AT
src: artifacts_indextts2_live3w id=fcd4efab-e98d-4186-92d2-35da0dbd0d4b score=39.6 audio=artifacts_indextts2_live3w/audio/fcd4efab-e98d-4186-92d2-35da0dbd0d4b.wav

38. score=31.8 cer=0.44 crit=0.00 tags=mixed_lang
GT: 请访问 https://example.com/reset?token=abc123 完成重置。
ASR: 请访问HTTPS Example Commerce Set Token等于ABC123完成重置
subs: httpse->HTTPSE; =abc->于ABC; .co->Com
src: artifacts_indextts2_live3w id=bb874b69-4101-4b01-b1f1-d3b78b3bf131 score=31.8 audio=artifacts_indextts2_live3w/audio/bb874b69-4101-4b01-b1f1-d3b78b3bf131.wav

39. score=24.6 cer=0.31 crit=0.00 tags=mixed_lang
GT: 服务跑在 us-east-1a，延迟从 23ms 上升到 120ms。
ASR: 服务跑在US-East-EA 延迟从23毫秒上升到120毫秒
subs: 1a->EA; ms->毫秒; us->US
src: artifacts_indextts2_target1 id=f470e83d-1dc4-418f-bbd6-63b23d74b384 score=24.6 audio=artifacts_indextts2_target1/audio/f470e83d-1dc4-418f-bbd6-63b23d74b384.wav

40. score=22.6 cer=0.29 crit=0.00 tags=mixed_lang
GT: 请把日志发到 ops-alert@company.com，主题写 CPU 过热。
ASR: 请把日志发到OPUS Alert Company Comp 主题写CPU过热
subs: ops-a->OPUSA; c->C
src: artifacts_indextts2_live3w id=cefe9d95-285b-4bcb-a71e-e534332d04b6 score=22.6 audio=artifacts_indextts2_live3w/audio/cefe9d95-285b-4bcb-a71e-e534332d04b6.wav

41. score=20.5 cer=0.25 crit=0.00 tags=mixed_lang
GT: 请用 JSON schema 校验输出，避免 parse error。
ASR: 请用Jason Schema校验输出 避免Parse Error
subs: SONs->sonS; e->E; p->P
src: artifacts_indextts2_live3w id=c68c9cd7-5c52-4c79-b99e-7b7e220095e0 score=20.5 audio=artifacts_indextts2_live3w/audio/c68c9cd7-5c52-4c79-b99e-7b7e220095e0.wav

### 标点与符号 (2)
42. score=32.0 cer=0.38 crit=0.00 tags=punctuation
GT: 她问：『你确定吗？』我答：『确定。』然后就挂断了。
ASR: 他问他你确定吗 拽我搭传确定 拽然后就挂断了
subs: 她->他; 答->传
src: artifacts_indextts2_live3w id=23e9e901-74b5-48a8-9878-ea7c0712c772 score=32.0 audio=artifacts_indextts2_live3w/audio/23e9e901-74b5-48a8-9878-ea7c0712c772.wav

43. score=22.6 cer=0.29 crit=0.00 tags=punctuation
GT: 请在备注里写：『已核对，无误。』并签名。
ASR: 请在备注里写 其以核对 无误掐柄签名
subs: 已->以; 并->柄
src: artifacts_indextts2_live3w id=f35b28a2-d4ff-4527-84e6-6b839ac5a930 score=22.6 audio=artifacts_indextts2_live3w/audio/f35b28a2-d4ff-4527-84e6-6b839ac5a930.wav

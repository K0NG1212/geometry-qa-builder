"""Where in each paper every borrowed number sits, for the paper-parameter families (cholesteric, moire, vortex).

The design and evidence cards carry a locator per value already; these three families take only a handful of numbers from
their papers, so the places live here, next to the builders that use them, and go into each family's sources.json. Read from
the local full texts on 2026-11-02; nothing was downloaded. Positions and numbers only: none of these papers licenses the
reproduction of its text or figures, so no sentence of theirs is copied here.
"""
from collections import OrderedDict

READ_ON = '2026-11-02'

# paper: (local copy, its SHA-256 as inputs/papers/SHA256SUMS.txt recorded it at download time). The copies live outside Git,
# so the checksum is stored rather than recomputed and a builder still runs on a machine that does not have the papers.
FULL_TEXT = {
    'shaban': ('inputs/papers/shaban2024/shaban2024-PMC11509098.xml',
               '221d5c74d191071399f7140592e5f8f66035eb30ff8c5c26eabd465674349ee7'),
    'dinc': ('inputs/papers/dinc2024/dinc2024-PMC11492181.xml',
             '0d5e717d7de7e11502f712f07ad36086a847be90f84e61457e3a05c0fc135d3b'),
    'cao': ('inputs/papers/cao2018/cao2018-arxiv-1803.02342.pdf',
            'da2dcac4e18f41fa4ee3599a653f57c1e1b63c1d881bd3d0fe05dd3152cabea5'),
    'kerelsky': ('inputs/papers/kerelsky2019/kerelsky2019-arxiv-1812.08776.pdf',
                 'ef069115e3c393344bb2e87775961fabe43004054f0a501c589f6e549a9f20ef'),
    'cottet': ('inputs/papers/cottet2014/cottet2014-arxiv-1401.4062.pdf',
               '874e6ec52fbed67bc893695c522cc0d45e5db013386d0baa01262209113e8c90'),
    'schaefermeier': ('inputs/papers/schaefermeier2026/schaefermeier2026-arxiv-2602.13060.pdf',
                      '0b6a7a9c5ceb9c3250d2b67b1ec8c95aa2d81ac6884b12e291e03660389409a5'),
}

PLACES = {
    'shaban': {
        'e44': '§2.2 Preparation of LC Cell Samples：ne = 1.7904、no = 1.5484，λ = 589 nm，T = 20 °C（同一句另给 ε∥ = 22.4、ε⊥ = 5.2）。',
        'htp_per_um': '§2.1 Materials：R5011 与 S5011 在 E44 中的 HTP = 107.5 μm⁻¹；§3.5 推导节距时复述同一数值。',
        'measured_reflection_nm': '§3.5（Figure 9a,b）：λc = 585 ± 1 nm（E44 + 2.62 wt% R5011）、λc = 593 ± 3 nm（E44 + 2.57 wt% S5011），均在 20 °C。',
        'model_concentrations': '§2.1 给出掺杂浓度范围 0.5–4.0 wt%。2.20 / 2.40 / 2.90 / 3.00 / 3.40 wt% 这五个浓度是本库在该范围内另取的设计候选，'
                                '节距由式 (7) 算出，论文没有给这五个值。',
        'pitch_nm': '§3.5 式 (7) p = 1/(HTP·c)：E44/R5011 p = 0.355 μm、E44/S5011 p = 0.362 μm。',
    },
    'dinc': {
        'average_refractive_index': 'Introduction：胆甾相聚合物的平均折射率「典型约 1.6」。本库按 λ = n·p 用这个 1.6 反推节距（419 / 377 nm）。',
        'concentration': 'Experimental · Preparation of CLC polymer coatings：LRCD 5.6 wt%（56.2 mg 对 920.8 mg Lumogen S1065）、RRCD 4.7 wt%。',
        'measured_reflection_nm': 'Results and discussion（Fig. 3）：LRCD 涂层反射峰 670 nm、RRCD 涂层反射带 603 nm。',
    },
    'cao': {
        'lattice_constant_nm': '正文定义超晶格密度 ns = 4/A 的一段，同句给出石墨烯晶格常数 a = 0.246 nm。',
        'twist_deg': 'M1 θ = 1.16°、M2 θ = 1.05°：Fig. 1b 图注，以及正文介绍两个 magic-angle 器件的一段；'
                     'D1 θ = 1.08°：Extended Data Fig. 2 图注与该节正文。',
    },
    'kerelsky': {
        'period_relation': '正文（“tear and stack”一段）：莫尔周期 λ = a/(2 sin(θ/2))，不含晶格弛豫与异质应变。',
        'twist_deg': 'Fig. 1 图注 (d–f)：2.02° / 0.79° / 1.10° 的原子分辨 STM 形貌；'
                     'Fig. 2a 的 LDOS 曲线同样按 3.48 / 2.02 / 1.59 / 1.10 / 0.79° 标注。',
    },
    'cottet': {
        'field_T': 'Figure 3（5 K 下不同磁场的涡旋图像序列，磁场标在每幅图上）与同一段正文：序列从 50.8 G 起、升到 188.7 G；'
                   '56.1 G 另见 Figure 4A 图注，56.1 G 与 117.3 G 见 Figure 4B 图注的放大图。',
        'triangular_lattice_d': 'Figure 4B 图注：三角点阵 d = 1.075、正方点阵 d = 1（rij = d·√(Φ0/B)）。'
                                '（Fig. 5 讲的是六重参数 |ψ6|，不是这个值。）',
    },
    'schaefermeier': {
        'conditions': 'T = 71 K、Bz = 3.7 mT 场冷：Figure 2 图注与方法一节。',
        'measured_spacing_nm': '正文 Results（Figure 2，BSCCO-2212）：FFT 一阶峰半径 f = 1.35 μm⁻¹，按 a = 2/(√3 f) 得 a ≈ 0.855 μm，'
                               '对应有效场约 3.26 mT。',
    },
}

NOTES = {
    'cholesteric': '每个取自论文的数都记了它在原文的位置（节号、式号、图号），2026-11-02 读本机全文核对，没有下载新文件。'
                   '两篇都是 CC BY，但这里只记位置与数值，不转载原文句子。',
    'moire': '每个取自论文的数都记了它在原文的位置（图注、正文段落），2026-11-02 读本机 PDF 核对，没有下载新文件。'
             '两篇都是 arXiv 预印本（非独占许可，不授权第三方转载），所以只记位置与数值，不转载原文句子与图。',
    'vortex': '每个取自论文的数都记了它在原文的位置（图号、图注、正文段落），2026-11-02 读本机 PDF 核对，没有下载新文件。'
              'Schäfermeier 2026 是 CC BY-NC-ND，Cottet 2014 是 arXiv 非独占许可，所以只记位置与数值，不转载原文句子与图。'
              '另：文件名里的 508G / 561G / 1173G / 1887G 是省掉小数点的写法，实际场是 50.8 / 56.1 / 117.3 / 188.7 G'
              '（field_T 与间距都按实际值算）；改名会动已发布资产的哈希，留到下次重跑。',
}


def locators(paper):
    """The locators block for one paper, plus the local full text it was read from."""
    path, sha256 = FULL_TEXT[paper]
    return OrderedDict(locators=OrderedDict(sorted(PLACES[paper].items())), locators_read_on=READ_ON,
                       full_text_read=OrderedDict(path=path, sha256=sha256))

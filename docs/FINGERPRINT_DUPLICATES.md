# Diagnostica duplicati delle fingerprint

Nessuna fusione o modifica del catalogo. Gli hash identici assegnati a identità diverse sono esclusi dal bundle attivo. Le similarità sono diagnostiche, non revisioni editoriali.

| Classe | Gruppi/coppie |
|---|---:|
| same_identity_multiple_resources | 0 |
| version_siblings | 3 |
| likely_duplicate_identities | 0 |
| shared_attachment | 3 |
| template_family | 133 |

Classi: stessa identità con più risorse; fratelli di versione; possibili identità duplicate; allegato condiviso; famiglia di template. Per le coppie non identiche la classificazione è euristica da metadati e overlap bottom-k ≥0,70. Il conteggio delle coppie non è il numero di gruppi disgiunti.

| Identità | Classe | Overlap |
|---|---|---|
| [16, 17] | template_family | 0.7721518987341772 |
| [16, 885] | template_family | 0.8006329113924051 |
| [17, 885] | template_family | 0.8966565349544073 |
| [20, 26] | template_family | 0.927734375 |
| [24, 25] | template_family | 0.7262357414448669 |
| [28, 886] | template_family | 0.85546875 |
| [31, 879] | template_family | 0.9410029498525073 |
| [86, 116] | version_siblings | 0.9345991561181435 |
| [87, 102] | version_siblings | 0.90625 |
| [89, 112] | version_siblings | 0.869140625 |
| [93, 303] | template_family | 1.0 |
| [94, 97] | template_family | 0.783203125 |
| [98, 101] | template_family | 0.72265625 |
| [123, 124] | template_family | 0.8783783783783784 |
| [153, 1224] | template_family | 0.720703125 |
| [155, 156] | template_family | 0.8166089965397924 |
| [253, 254] | template_family | 0.7235294117647059 |
| [253, 255] | template_family | 0.7705882352941177 |
| [279, 280] | template_family | 0.900523560209424 |
| [279, 281] | template_family | 0.8272251308900523 |
| [280, 281] | template_family | 0.8229166666666666 |
| [287, 288] | template_family | 0.734375 |
| [289, 290] | template_family | 0.8703071672354948 |
| [401, 468] | template_family | 0.8678414096916299 |
| [402, 464] | template_family | 0.7100371747211895 |
| [402, 506] | template_family | 0.909433962264151 |
| [404, 441] | template_family | 0.8130841121495327 |
| [404, 534] | template_family | 0.8130841121495327 |
| [405, 434] | template_family | 0.9027027027027027 |
| [406, 435] | template_family | 0.8629441624365483 |
| [406, 527] | template_family | 0.8426395939086294 |
| [407, 442] | template_family | 0.8318965517241379 |
| [407, 516] | template_family | 0.8461538461538461 |
| [407, 535] | template_family | 0.8318965517241379 |
| [408, 436] | template_family | 0.8426395939086294 |
| [408, 509] | template_family | 0.8492462311557789 |
| [410, 443] | template_family | 0.8943661971830986 |
| [410, 536] | template_family | 0.8888888888888888 |
| [411, 444] | template_family | 0.9285714285714286 |
| [411, 518] | template_family | 0.896551724137931 |
| [412, 445] | template_family | 0.9501084598698482 |
| [413, 446] | template_family | 0.7547169811320755 |
| [413, 474] | template_family | 0.7592592592592593 |
| [413, 520] | template_family | 0.7454545454545455 |
| [413, 539] | template_family | 0.7547169811320755 |
| [415, 437] | template_family | 0.8580645161290322 |
| [415, 469] | template_family | 0.7169811320754716 |
| [415, 511] | template_family | 0.8535031847133758 |
| [416, 433] | template_family | 0.7048192771084337 |
| [416, 447] | template_family | 0.9078947368421053 |
| [416, 505] | template_family | 0.7065868263473054 |
| [416, 540] | template_family | 0.9078947368421053 |
| [417, 448] | template_family | 0.8481675392670157 |
| [417, 522] | template_family | 0.8186528497409327 |
| [417, 541] | template_family | 0.8481675392670157 |
| [418, 449] | template_family | 0.8220338983050848 |
| [418, 523] | template_family | 0.8099173553719008 |
| [418, 542] | template_family | 0.8227848101265823 |
| [419, 438] | template_family | 0.9456066945606695 |
| [419, 531] | template_family | 0.9497907949790795 |
| [420, 440] | template_family | 0.8838174273858921 |
| [421, 439] | template_family | 0.8162544169611308 |
| [421, 513] | template_family | 0.8245614035087719 |
| [421, 532] | template_family | 0.8297872340425532 |
| [433, 447] | template_family | 0.7530120481927711 |
| [433, 505] | template_family | 0.8855421686746988 |
| [433, 540] | template_family | 0.7108433734939759 |
| [435, 527] | template_family | 0.8781725888324873 |
| [436, 509] | template_family | 0.8477157360406091 |
| [437, 469] | template_family | 0.7354838709677419 |
| [437, 511] | template_family | 0.8516129032258064 |
| [438, 531] | template_family | 0.9456066945606695 |
| [439, 513] | template_family | 0.872791519434629 |
| [439, 532] | template_family | 0.8900709219858156 |
| [441, 534] | template_family | 0.9158878504672897 |
| [442, 516] | template_family | 0.8318965517241379 |
| [442, 535] | template_family | 0.853448275862069 |
| [443, 536] | template_family | 0.9014084507042254 |
| [444, 518] | template_family | 0.9285714285714286 |
| [446, 474] | template_family | 0.7547169811320755 |
| [446, 520] | template_family | 0.7547169811320755 |
| [446, 539] | template_family | 0.7735849056603774 |
| [447, 505] | template_family | 0.7005988023952096 |
| [447, 540] | template_family | 0.9166666666666666 |
| [448, 522] | template_family | 0.8219895287958116 |
| [448, 541] | template_family | 0.8534031413612565 |
| [449, 523] | template_family | 0.8601694915254238 |
| [449, 542] | template_family | 0.8686440677966102 |
| [464, 506] | template_family | 0.7433962264150943 |
| [469, 511] | template_family | 0.732484076433121 |
| [474, 520] | template_family | 0.8518518518518519 |
| [474, 539] | template_family | 0.7547169811320755 |
| [478, 479] | template_family | 0.869140625 |
| [480, 482] | template_family | 0.8355263157894737 |
| [482, 483] | template_family | 0.7294117647058823 |
| [486, 487] | template_family | 0.9345238095238095 |
| [503, 504] | template_family | 0.8359375 |
| [505, 540] | template_family | 0.718562874251497 |
| [513, 532] | template_family | 0.9078014184397163 |
| [516, 535] | template_family | 0.875 |

Elenco completo: `benchmarks/results/round5/fingerprint_duplicates.json`. Nessuna classificazione attribuisce una verifica umana o autorizza un auto-merge.

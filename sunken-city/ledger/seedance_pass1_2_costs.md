# Costs, scene 01 Seedance package (budget 3.00 USD)

All gpt-image-edit at 0.22995 USD per image. No video generation run.

| Item | Job | Cost |
|---|---|---|
| A5 v2 (charsheet redo, edit of B1) | mjob_90866405346c | 0.23 |
| K000 | mjob_e9a3fb43c915 | 0.23 |
| K096 | mjob_846f25c1c6c6 | 0.23 |
| K110 | mjob_7336c52306f4 | 0.23 |
| K192 | mjob_bb2a2080993e | 0.23 |
| K288 | mjob_a088c2c84108 | 0.23 |
| K384 | mjob_60b97ee40fe9 | 0.23 |
| K480 | mjob_7ca9b081282c | 0.23 |
| K575 | mjob_f4bd9506efc8 | 0.23 |
| A6 first try (content-policy rejection, reservation not released on the job) | mjob_154efde5f4b3 | 0 to 0.23 |
| A6 second try | mjob_5b72e0ccb7a5 | 0.23 (delivered) |

Total: 2.30 USD for 10 delivered images (A5 v2, 8 keyframes, A6), plus 0 to 0.23 for the rejected A6 first try. Uploads are free. No keyframe redos.

## Estimated Seedance 2.5 cost (seedance-25-i2v, 24 s = 6 clips x 4 s)
- 480p draft: 24 s x 0.23153 = 5.56 USD (0.93 per 4 s clip)
- 720p: 24 s x 0.49665 = 11.92 USD (1.99 per clip)
- success rate 82% over 7 days, effective cost about 6.78 USD (480p) / 14.53 USD (720p) with retries
- Test lane seedance-mini-ref2v, 8 s: about 1.30 USD

## Final-fix round (budget 1.00 USD)
K000 v2 0.23 (mjob_6ab43c9f7e8e), K096 v2 0.23 (mjob_2852c43fc216, not adopted: sun column no closer, v1 kept), A5 v3 0.23 (mjob_d46cb6d78c9f), A6 redo rejected by content checker (mjob_caaf040898d9, 0 to 0.23). Round total 0.69 to 0.92. Grand total about 2.99 to 3.22 USD.

## Round p3 (previs v3 rebuild, budget 3.00 USD)
B1 v2 0.2216 (gpt-image mjob_6571d7cb5824), C1 v2 0.2216 (mjob_c78a1d93882a), A5 v4 0.23 (mjob_106956212e19), K000 0.23 + redo 0.23 (mjob_a092a4326c36, mjob_69e3d42a1ad8), K096 0.23 (mjob_ddd25ba61dec), K110 0.23 (mjob_7ac867955140; first try rejected by the content checker, reservation released), K192 0.23 (mjob_ef30bdcec257), K288 0.23 (mjob_fe2a3f739edb), K384 0.23 (mjob_16c3cdada3e7), K480 0.23 (mjob_a361b5b9c506), K575 0.23 + redo 0.23 (mjob_5f288da4c69e, mjob_248d4bf98f44).
Round total: 2.97 USD. Seedance estimate unchanged: 6 x 4 s = 5.56 USD at 480p, 11.92 USD at 720p.

## Realism pass + Seedance 480p (this run)
Realism edits, gpt-image-edit 0.22995 each, 13 calls = 2.99 USD: K000 r1 mjob_bb143e932bf3 (rejected: reframed), K000 r2 mjob_3cf47c0fe564 (adopted), K096 mjob_fd9dcb7ec761, K110 mjob_f2f96152455c, K192 mjob_5ecdec45be40, K288 mjob_ab2add83884d, K384 mjob_dececd4fa68f, K480 mjob_b92f0ec57142, K575 mjob_96117ae0ac11, A1 mjob_5c4f81d0024b, A5 mjob_c18df74d0947, B1 mjob_668b8ae542b4, C1 mjob_ced5bf697fa0. Previs frame not passed as a second image (could not be uploaded); stricter "pixel-aligned retouch" prompt used instead.
Seedance 2.5 480p, 0.9261 each: c1 mjob_fdf1f1fcefac, c2 mjob_7a7d74b9959a, c3 mjob_bad97e3eba1d, c4 mjob_2c4300ec5ade = 3.70 USD. c5, c6 not run (launch of c5 was denied by the permission classifier).
Running total 6.69 USD of 12.
Clips 5 and 6 (0.9261 each): c5 mjob_84dabad6b520 (key sc01_sd_c5_v2; the v1 launch was denied before submit, nothing billed), c6 mjob_5a64a4ba4f0b. Seedance total 6 x 0.9261 = 5.56 USD. Images 2.99. GRAND TOTAL this run 8.55 USD of 12. No retries of provider failures.

## Drowned Athens redo (BRIEF_athens.md, budget cap 11 USD)
Part 1 (charsheet/C, 2 USD budget): C1 gpt-image 0.2216 (mjob_06b5c21d2b9f); C2-C6 gpt-image-edit 0.23 each (mjob_0d6f93802c61, mjob_912b055d58b8, mjob_adc9ae3f1b71, mjob_3cc69b77f918, mjob_8cc17eb8ab52) = 1.37.
Part 2 (keyframes): K110 mjob_aee84397fee8, K192 mjob_5351c3bd4ab5, K288 mjob_7c057a54af55, K384 mjob_a106db45ea73, K480 mjob_0f4dfa3aab04, K575 v1 mjob_cec75e20921c (window 7% too narrow, not adopted), K575 v2 mjob_fac54ba2b4c8 (adopted) = 7 x 0.23 = 1.61. Composition reference = currently hosted keyframes (previs frames not uploaded).
Part 3 (seedance-25-i2v 480p, 0.9261 each): c2 mjob_ddfa62b92646, c3 v1 mjob_e57eb0fc84db (first frame did not match K192, discarded), c3 v2 mjob_572846f7e608, c4 mjob_1725602e4fee, c5 mjob_fab363171805, c6 mjob_ca2fd823232d = 6 x 0.9261 = 5.56.
TOTAL 8.54 USD of 11. No call denied. Stopped before 720p.

from PIL import Image, ImageDraw, ImageFont
P = '/home/claude/val/paper/'; T = '/home/claude/val/tool/'
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 26); FB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 28)
s = 1 / 0.6773
def crop(fig, box): im = Image.open(P + fig).convert('RGB'); return im.crop(tuple(int(v * s) for v in box))
C1, C2, C3 = (25, 475), (485, 905), (910, 1395); R1, R2, R3 = (0, 262), (300, 582), (605, 897)
fig4 = lambda c, r: crop('F4.png', (c[0], r[0], c[1], r[1]))
PAN = {
 'F2a': (crop('F2.png', (0, 60, 690, 510)), 'Fig. 2a · consensus ARTN, ε = 2/decade', 'Network · PIKART only · centroid · ε = 2/decade'),
 'F2b': (crop('F2.png', (700, 0, 1400, 510)), 'Fig. 2b · node strength', 'Hubs · node strength (in + out) · centroid · ε = 8 ARs (as Fig2_NodeImportance.py)'),
 'F2c': (crop('F2.png', (0, 555, 690, 1068)), 'Fig. 2c · node divergence (head file)', 'Hubs · divergence · head · ε = 8 ARs'),
 'F2d': (crop('F2.png', (700, 555, 1400, 1068)), 'Fig. 2d · PageRank (head file)', 'Hubs · PageRank α = 0.9 · head · ε = 8 ARs'),
 'F3a': (crop('F3.png', (0, 0, 1400, 860)), 'Fig. 3a · net IVT change at nodes', 'Hubs · net IVT change at node · centroid · ε = 2/decade'),
 'F4a': (fig4(C1, R1), 'Fig. 4a · highways (EBC), PIKART purple', 'Highways · road types · ε = 2/decade'),
 'F4b': (fig4(C2, R1), 'Fig. 4b · net IVT change along highways', 'Highways · IVT gain or loss'),
 'F4d': (fig4(C1, R2), 'Fig. 4d · colour bars: DJF purple, JJA green', 'Highways · compare DJF (purple, 5 ARs) and JJA (green, 4 ARs) · match rule'),
 'F4e': (fig4(C2, R2), 'Fig. 4e · "DJF", IVT change', 'Highways · IVT gain or loss · DJF (5 ARs)'),
 'F4f': (fig4(C3, R2), 'Fig. 4f · "JJA", IVT change', 'Highways · IVT gain or loss · JJA (4 ARs)'),
 'F4g': (fig4(C1, R3), 'Fig. 4g · El Niño (green) vs La Niña (purple)', 'Highways · compare La Niña (purple, 4 ARs) and El Niño (green, 3 ARs)'),
 'F4h': (fig4(C2, R3), 'Fig. 4h · El Niño, IVT change', 'Highways · IVT gain or loss · El Niño (3 ARs)'),
 'F4i': (fig4(C3, R3), 'Fig. 4i · La Niña, IVT change', 'Highways · IVT gain or loss · La Niña (4 ARs)'),
 'F5a': (crop('F5.png', (0, 0, 1400, 575)), 'Fig. 5a · Infomap basins (consensus, ε = 8 ARs)', 'Basins · PIKART · ε = 8 ARs · seed 38, 5 trials · ≥ 15 cells'),
 'F5b': (crop('F5.png', (0, 735, 640, 905)), 'Fig. 5b (top) · upstream of a NE American basin', 'Basins · upstream of the basin containing 47°N, 78°W'),
}
def pair(name, H=560):
    pimg, pcap, tcap = PAN[name]; timg = Image.open(T + name + '.png').convert('RGB')
    sc = lambda im: im.resize((int(im.width * H / im.height), H), Image.LANCZOS)
    a, b = sc(pimg), sc(timg); pad = 20; top = 60
    W = a.width + b.width + 3 * pad; out = Image.new('RGB', (W, H + top + pad), 'white'); d = ImageDraw.Draw(out)
    out.paste(a, (pad, top)); out.paste(b, (2 * pad + a.width, top))
    d.text((pad, 14), 'Paper  ' + pcap, font=FB if False else F, fill=(30, 35, 48)); d.text((2 * pad + a.width, 14), 'Tool  ' + tcap, font=F, fill=(30, 35, 48))
    d.rectangle([pad - 1, top - 1, pad + a.width, top + H], outline=(200, 205, 210)); d.rectangle([2 * pad + a.width - 1, top - 1, 2 * pad + a.width + b.width, top + H], outline=(200, 205, 210))
    out.save(f'/home/claude/val/sbs/{name}.png'); return out
for k in PAN: pair(k)
# season hypothesis sheet: paper 4e/4f against tool DJF, JJA, MAM, SON
H = 330; ims = [fig4(C2, R2), fig4(C3, R2)] + [Image.open(T + n + '.png').convert('RGB') for n in ['F4e', 'F4f', 'F4e_MAM', 'F4f_SON']]
labs = ['Paper 4e "DJF"', 'Paper 4f "JJA"', 'Tool DJF', 'Tool JJA', 'Tool MAM', 'Tool SON']
ims = [im.resize((int(im.width * H / im.height), H), Image.LANCZOS) for im in ims]
w = max(i.width for i in ims); out = Image.new('RGB', (2 * w + 60, 3 * (H + 50) + 20), 'white'); d = ImageDraw.Draw(out)
for i, (im, lab) in enumerate(zip(ims, labs)):
    x = 20 + (i % 2) * (w + 20); y = 10 + (i // 2) * (H + 50); d.text((x, y), lab, font=F, fill=(30, 35, 48)); out.paste(im, (x, y + 40))
out.save('/home/claude/val/sbs/seasons_check.png'); print('ok')

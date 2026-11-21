"""Verifica que una reescritura de historial con git filter-repo solo cambio lo previsto.

Uso: python -I verificar_historial.py --old ORIGINAL.git --new REESCRITO.git --rules REEMPLAZOS.txt

No contiene datos sensibles: los patrones se leen del archivo de reemplazos (fuera del repositorio).
Comprobaciones:
  a) cero coincidencias de cada patron en TODAS las revisiones (contenido), mensajes, nombres de
     archivo y etiquetas anotadas;
  b) mismas fechas de autor y de commit, autores, orden, asuntos y padres (solo cambian los SHA);
  c) por cada par de commits antiguo/nuevo: misma lista de archivos y modos, y las lineas que
     difieren contienen un patron en el original y ninguno en el nuevo.
Sale con codigo 1 si alguna comprobacion falla.
"""

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if check and r.returncode not in (0, 1):
        sys.exit(f"git {' '.join(args)} fallo en {repo}: {r.stderr.decode(errors='replace')[:300]}")
    return r.stdout


def load_rules(path):
    """Devuelve lista de (patron_str, es_regex). Solo se usa el lado izquierdo."""
    rules = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "==>" not in raw:
            continue
        lhs = raw.split("==>", 1)[0]
        if lhs.startswith("regex:"):
            rules.append((lhs[len("regex:"):], True))
        elif lhs.startswith("literal:"):
            rules.append((re.escape(lhs[len("literal:"):]), True))
        else:
            rules.append((re.escape(lhs), True))
    return rules


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--rules", required=True)
    a = ap.parse_args()
    old, new = Path(a.old), Path(a.new)
    rules = load_rules(a.rules)
    pats = [p for p, _ in rules]
    cre = [re.compile(p) for p in pats]
    failures = []

    def fail(msg):
        failures.append(msg)
        print("  FALLO:", msg)

    # --- mapa de commits ---------------------------------------------------------------
    cmap = {}
    cm = new / "filter-repo" / "commit-map"
    lines = cm.read_text().splitlines()[1:]
    for ln in lines:
        o, n = ln.split()
        cmap[o] = n
    old_commits = git(old, "rev-list", "--all", "--topo-order").decode().split()
    new_commits = git(new, "rev-list", "--all", "--topo-order").decode().split()
    print(f"Commits: original={len(old_commits)} nuevo={len(new_commits)} entradas en commit-map={len(cmap)}")
    if len(old_commits) != len(new_commits):
        fail("distinto numero de commits")
    missing = [c for c in old_commits if cmap.get(c, "0" * 40) == "0" * 40]
    if missing:
        fail(f"{len(missing)} commits sin equivalente en commit-map")

    # --- (a) cero coincidencias --------------------------------------------------------
    print("(a) Cero coincidencias en todas las revisiones")
    print(f"    patrones: {len(pats)}")
    args = ["grep", "-P", "-I", "-l"]
    for p in pats:
        args += ["-e", p]
    r = subprocess.run(
        ["git", "-C", str(new), *args, *new_commits], capture_output=True
    )
    hits = [x for x in r.stdout.decode(errors="replace").splitlines() if x]
    print(f"    revisiones x archivos revisados con coincidencias (contenido): {len(hits)}")
    if hits:
        # no se imprime el contenido; solo ruta y revision corta
        for h in hits[:10]:
            print("     ", h[:60])
        fail(f"{len(hits)} coincidencias en contenido")
    msgs = git(new, "log", "--all", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x01").decode(errors="replace")
    bad_msgs = [m for m in msgs.split("\x01") if any(c.search(m) for c in cre)]
    print(f"    mensajes/autores con coincidencias: {len(bad_msgs)}")
    if bad_msgs:
        fail(f"{len(bad_msgs)} commits con coincidencias en mensaje o autor")
    names = set(git(new, "log", "--all", "--name-only", "--format=").decode(errors="replace").splitlines())
    bad_names = [n for n in names if any(c.search(n) for c in cre)]
    print(f"    nombres de archivo distintos revisados: {len(names)}; con coincidencias: {len(bad_names)}")
    if bad_names:
        fail("nombres de archivo con coincidencias (usar --path-rename)")
    tags = git(new, "for-each-ref", "--format=%(refname) %(contents)").decode(errors="replace")
    bad_tags = [t for t in tags.split("\n") if any(c.search(t) for c in cre)]
    print(f"    etiquetas/ramas con coincidencias (nombre o contenido): {len(bad_tags)}")
    if bad_tags:
        fail("etiquetas o refs con coincidencias")

    # --- (b) metadatos ----------------------------------------------------------------
    print("(b) Fechas, autores, orden, asuntos y padres")
    fmt = "%H%x00%P%x00%aI%x00%cI%x00%an%x00%ae%x00%cn%x00%ce%x00%s"

    def meta(repo):
        out = {}
        for ln in git(repo, "log", "--all", "--topo-order", f"--format={fmt}").decode(errors="replace").splitlines():
            h, p, ad, cd, an, ae, cn, ce, s = ln.split("\x00")
            out[h] = (p, ad, cd, an, ae, cn, ce, s)
        return out

    mo, mn = meta(old), meta(new)
    diff_meta = 0
    diff_subject = 0
    diff_parent = 0
    for o, n in cmap.items():
        if o not in mo or n not in mn:
            continue
        po, ado, cdo, ano, aeo, cno, ceo, so = mo[o]
        pn, adn, cdn, ann, aen, cnn, cen, sn = mn[n]
        if (ado, cdo, ano, aeo, cno, ceo) != (adn, cdn, ann, aen, cnn, cen):
            diff_meta += 1
        if so != sn:
            diff_subject += 1
        mapped_parents = " ".join(cmap.get(x, "?") for x in po.split())
        if mapped_parents != pn:
            diff_parent += 1
    print(f"    commits comparados: {len(cmap)}; fechas/autores distintos: {diff_meta}; asuntos distintos: {diff_subject}; padres distintos: {diff_parent}")
    if diff_meta:
        fail("fechas o autores cambiaron")
    if diff_parent:
        fail("la estructura de padres cambio")
    if diff_subject:
        print(f"    (aviso) {diff_subject} asuntos cambiaron: deben ser solo reemplazos")
    order_old = [cmap.get(c) for c in old_commits]
    same_order = order_old == new_commits
    if not same_order:
        # el orden puede variar solo en empates de fecha: comparar por (fecha de commit) ordenado
        dold = [mo[c][2] for c in old_commits]
        dnew = [mn[c][2] for c in new_commits]
        same_order = dold == dnew
        print("    orden topologico por SHA: distinto; orden de fechas de commit:", "igual" if same_order else "DISTINTO")
        if not same_order:
            fail("el orden de los commits cambio")
    else:
        print("    orden topologico: identico (por commit-map)")

    # --- (c) archivos y diferencias ---------------------------------------------------
    print("(c) Por cada par de commits: mismos archivos y solo lineas con reemplazos")

    def tree(repo, c):
        out = git(repo, "ls-tree", "-r", "-z", c).split(b"\x00")
        t = {}
        for e in out:
            if not e:
                continue
            meta_, path = e.split(b"\t", 1)
            mode, typ, sha = meta_.split()
            t[path] = (mode, sha.decode())
        return t

    def blob(repo, sha):
        return subprocess.run(["git", "-C", str(repo), "cat-file", "blob", sha], capture_output=True).stdout

    pair_cache = {}
    commits_with_changes = 0
    file_mods = 0
    files_diff_list = 0
    unexpected = []
    for o, n in cmap.items():
        if o not in mo:
            continue
        to, tn = tree(old, o), tree(new, n)
        if set(to) != set(tn) or any(to[k][0] != tn[k][0] for k in to):
            files_diff_list += 1
            unexpected.append(f"lista de archivos distinta en {o[:8]}->{n[:8]}")
            continue
        changed = [k for k in to if to[k][1] != tn[k][1]]
        if changed:
            commits_with_changes += 1
        for k in changed:
            file_mods += 1
            key = (to[k][1], tn[k][1])
            if key in pair_cache:
                continue
            bo, bn = blob(old, to[k][1]), blob(new, tn[k][1])
            if b"\x00" in bo or b"\x00" in bn:
                pair_cache[key] = (0, 0, "binario modificado")
                unexpected.append(f"binario modificado: {k.decode(errors='replace')}")
                continue
            lo = bo.decode("utf-8", "surrogateescape").splitlines(keepends=True)
            ln_ = bn.decode("utf-8", "surrogateescape").splitlines(keepends=True)
            removed = added = 0
            problem = None
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, lo, ln_, autojunk=False).get_opcodes():
                if tag == "equal":
                    continue
                chunk_o = "".join(lo[i1:i2])
                chunk_n = "".join(ln_[j1:j2])
                removed += i2 - i1
                added += j2 - j1
                if not any(c.search(chunk_o) for c in cre):
                    problem = "linea cambiada sin patron en el original"
                if any(c.search(chunk_n) for c in cre):
                    problem = "linea nueva aun contiene un patron"
            pair_cache[key] = (removed, added, problem)
            if problem:
                unexpected.append(f"{problem}: {k.decode(errors='replace')}")
    rem = sum(v[0] for v in pair_cache.values())
    add = sum(v[1] for v in pair_cache.values())
    print(f"    pares de commits: {len(cmap)}; con archivos modificados: {commits_with_changes}")
    print(f"    modificaciones (commit, archivo): {file_mods}; versiones distintas de archivo: {len(pair_cache)}")
    print(f"    lineas quitadas: {rem}; lineas puestas: {add}; commits con lista de archivos distinta: {files_diff_list}")
    if unexpected:
        for u in sorted(set(unexpected))[:20]:
            print("     ", u)
        fail(f"{len(set(unexpected))} diferencias inesperadas")

    print()
    if failures:
        print(f"RESULTADO: FALLO ({len(failures)} comprobaciones)")
        sys.exit(1)
    print("RESULTADO: todas las comprobaciones (a, b, c) pasaron")


if __name__ == "__main__":
    main()

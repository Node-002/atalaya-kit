# Guía para activar las herramientas (orden de necesidad)

> Estado medido el 21 nov 2026 en tu equipo. Marca cada paso cuando lo hagas. Los comandos se ejecutan en PowerShell. Después de instalar programas, **cierra y vuelve a abrir la app de Claude** para que reconozca los nuevos comandos.

## Ya instalado (no hay que hacer nada)
Git, GitHub CLI (sesión iniciada como Node-002), Python 3.12, Node y npm, gitleaks, Chrome, Edge, Wireshark, WSL y winget. En el entorno del proyecto: pytest, pytest-cov, ruff, bandit y pip-audit.

## Necesarias hoy
- [ ] **1. Dependabot** (2 min, en el navegador): repositorio `Node-002/atalaya` → Settings → Advanced Security (o Code security) → activar *Dependabot alerts* y *Dependabot security updates*.
- [ ] **2. Permiso para el CI** (solo si GitHub rechaza subir `.github/workflows`): `gh auth refresh -h github.com -s workflow`
- [ ] **3. OWASP ZAP**: `winget install ZAP.ZAP`
- [ ] **4. Trivy**: `winget install AquaSecurity.Trivy`
- [ ] **5. ffuf**: `winget install ffuf.ffuf`
- [ ] **6. Nmap**: `winget install Insecure.Nmap`
- [ ] **7. Cerrar y reabrir la app**, y decirme «listo» para que verifique cada herramienta.
- [ ] **8. Cuenta en Render** (necesaria antes de desplegar).

## Las instalo yo
mypy (opcional), versiones fijadas de dependencias, GitHub Actions, Lighthouse con `npx`, y `pytest-cov` dentro de `requirements-dev.txt`.

## Opcionales
- [ ] Figma (cuenta gratis) para bocetos.
- [ ] Autorizar el conector de Canva para las diapositivas.
- [ ] Nuclei (descarga oficial de `projectdiscovery/nuclei` en GitHub, verificando el hash).
- [ ] testssl.sh: `git clone --depth 1 https://github.com/testssl/testssl.sh` y correrlo desde Git Bash o WSL.
- [ ] Semgrep: mejor dentro de WSL (en Windows nativo tiene soporte limitado).
- [ ] Burp Suite Community (ZAP ya cubre lo mismo).

## No hace falta
Docker Desktop (decisión del 21 nov: se prueba directo en Render), Kali, Metasploit y las herramientas de posexplotación o Wi-Fi.

# Déploiement Thée AI sur ton serveur (agenc-ai.com)

Ce guide déploie le backend FastAPI **sans toucher** au projet `aida` déjà en production.
Le widget tournera sur le port 8002, exposé via Nginx sur `/api/`.

---

## Étape 1 — Copier le projet sur le serveur

Sur ton Mac, dans le dossier du projet `immo-assistant` :

```bash
cd ~/Downloads/immo-assistant  # ou où se trouve le dossier dézippé
tar -czf thee-ai-backend.tar.gz app requirements.txt .env.example
```

Puis envoie-le sur le serveur :

```bash
scp thee-ai-backend.tar.gz root@\[2a02:4780:28:58d8::1\]:/var/www/
```

---

## Étape 2 — Sur le serveur : installer et configurer

```bash
cd /var/www
mkdir -p thee-ai-backend
tar -xzf thee-ai-backend.tar.gz -C thee-ai-backend
cd thee-ai-backend

# Environnement Python isolé
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Étape 3 — Configurer les variables d'environnement

```bash
cp .env.example .env
nano .env
```

Remplis avec :
```
OPENAI_API_KEY=sk-ta-cle-openai
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/thee_ai
SENDGRID_API_KEY=
FROM_EMAIL=contact@agenc-ai.com
CALENDLY_EVENT_URL=https://calendly.com/thee-ai/30min
SECRET_KEY=genere-une-cle-aleatoire-ici
ENVIRONMENT=production
ALLOWED_ORIGINS=*
```

Si tu n'as pas encore PostgreSQL sur ce serveur, utilise SQLite temporairement pour tester (voir note en bas).

---

## Étape 4 — Lancer le backend en arrière-plan (avec systemd)

Crée un service qui redémarre automatiquement :

```bash
cat > /etc/systemd/system/thee-ai.service << 'EOF'
[Unit]
Description=Thée AI Backend
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/thee-ai-backend
Environment="PATH=/var/www/thee-ai-backend/venv/bin"
ExecStart=/var/www/thee-ai-backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8002
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable thee-ai
systemctl start thee-ai
systemctl status thee-ai
```

Vérifie que ça tourne :
```bash
curl http://127.0.0.1:8002/health
```
Tu dois voir `{"status":"ok","env":"production"}`.

---

## Étape 5 — Exposer via Nginx sur agenc-ai.com/api/

On ajoute une route isolée, sans toucher au reste de `aida` :

```bash
sed -i "s|location /vente { return 301 /vente/; }|location /api/ {\n        proxy_pass http://127.0.0.1:8002/;\n        proxy_set_header Host \$host;\n        proxy_set_header X-Real-IP \$remote_addr;\n        add_header Access-Control-Allow-Origin *;\n    }\n    location /vente { return 301 /vente/; }|" /etc/nginx/sites-enabled/aida
nginx -t && systemctl reload nginx
```

Vérifie depuis l'extérieur :
```bash
curl https://agenc-ai.com/api/health
```

---

## Étape 6 — Héberger le widget JS

```bash
mkdir -p /var/www/html/widget
cp /var/www/thee-ai-backend/widget/thee-widget.js /var/www/html/widget/
```

Ajoute la route Nginx pour servir ce dossier (si pas déjà couvert par une route générique) :

```bash
sed -i "s|location /vente { return 301 /vente/; }|location /widget/ {\n        root /var/www/html;\n        add_header Access-Control-Allow-Origin *;\n    }\n    location /vente { return 301 /vente/; }|" /etc/nginx/sites-enabled/aida
nginx -t && systemctl reload nginx
```

Teste :
```
https://agenc-ai.com/widget/thee-widget.js
```

---

## Étape 7 — Snippet à donner à une agence

Une fois tout en place, voici ce que tu colles sur le site du client, juste avant `</body>` :

```html
<script
  src="https://agenc-ai.com/widget/thee-widget.js"
  data-agency="nom-agence-slug"
  data-name="Nom de l'agence"
  data-color="#1a56db">
</script>
```

---

## Note — si pas de PostgreSQL configuré

Pour tester rapidement sans base de données complexe, remplace dans `app/database.py` :

```python
DATABASE_URL = "sqlite+aiosqlite:///./thee_ai.db"
```

Et ajoute `aiosqlite` à `requirements.txt`. Ça crée un fichier local, suffisant pour les tests avant de basculer en PostgreSQL pour la prod.

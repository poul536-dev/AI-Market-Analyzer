# AI Market Analyzer - App Android

App para acessar a plataforma de analise de mercado B3 de qualquer lugar.

## COMO BAIXAR O APP

### Passo 1: Colocar o Backend Online

1. Crie conta no https://github.com
2. Crie um repositório chamado `AI-Market-Analyzer`
3. Faça upload de TODOS os arquivos do projeto
4. Crie conta no https://railway.app (entre com GitHub)
5. Clique em "New Project" > "Deploy from GitHub repo"
6. Selecione seu repositório
7. Em "Variables", adicione:

```
AUTH_SECRET_KEY=xlBv21gympDb99Im5u_pOsO2nAnlpeYVadERD8SYOcXyk_v8RmjLPv6z2HzYwYv5s1MSC5Ly-yVp-eYkUYZehA
AUTH_TOKEN_EXPIRE_MINUTES=1440
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
MT5_LOGIN=0
MT5_SERVER=
MT5_PASSWORD=
```

8. Aguarde o deploy (~3 min)
9. Anote a URL gerada (ex: `ai-market-analyzer.up.railway.app`)

### Passo 2: Configurar URL no App

1. No GitHub, vá em `android-app/app/src/main/res/values/strings.xml`
2. Clique no ícone de editar
3. Troque a URL:
```xml
<string name="server_url">https://SUA-URL.up.railway.app</string>
```
4. Clique em "Commit changes"
5. O APK será rebuildado automaticamente

### Passo 3: Baixar o APK

1. No GitHub, vá na aba "Actions"
2. Clique em "Build Android APK"
3. Clique em "Run workflow" (se não rodou automático)
4. Aguarde ~5 minutos
5. Clique na execução que aparecer
6. Em "Artifacts", baixe `AI-Market-Analyzer-debug`
7. Transfira o arquivo ZIP para o celular
8. Extraia o APK do ZIP

### Passo 4: Instalar no Celular

1. No celular, toque no arquivo APK
2. Se pedir, ative "Fontes desconhecidas":
   - Android 8+: Configurações > Apps > especial > Fontes desconhecidas
3. Clique em "Instalar"
4. Clique em "Abrir"

### Passo 5: Usar

1. Abra o app
2. Login: `admin` / `admin123`
3. Dashboard com dados em tempo real!

---

## FUNCIONALIDADES

- Splash screen animada
- Dashboard completo
- Pull-to-refresh (puxe para atualizar)
- Botão voltar nativo
- Tela de erro sem internet
- Full screen (sem barra de endereco)
- Tema escuro
- Android 7.0+ (API 24+)

---

## ESTRUTURA DO APP

```
android-app/
├── build.gradle
├── settings.gradle
├── gradlew / gradlew.bat
├── app/
│   ├── build.gradle
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── java/.../
│       │   ├── SplashActivity.java
│       │   └── MainActivity.java
│       └── res/
│           ├── layout/
│           ├── values/
│           ├── drawable/
│           └── mipmap-*/
```

---

## PROBLEMAS COMUNS

**App não conecta:**
- Verifique se o Railway está rodando
- Teste a URL no navegador do celular
- Verifique se a URL está correta no strings.xml

**APK não instala:**
- Ative "Fontes desconhecidas"
- Android 8+: Configurações > Apps > Desconhecidos

**Build falha no GitHub:**
- Verifique se tudo foi commitado
- Actions > clique na execução > veja o erro

**Login não funciona:**
- Senha: admin123
- Se esqueceu, delete users.json no Railway

---

## CUSTO

Tudo gratuito:
- GitHub: gratis
- Railway: gratis (500h/mes)
- App: gratis

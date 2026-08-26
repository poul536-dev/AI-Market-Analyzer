# COMO BAIXAR E USAR O APP ANDROID

## PASSO 1: Colocar o Backend Online (Railway)

### 1.1 Criar conta no GitHub
1. Acesse https://github.com
2. Clique em "Sign up"
3. Crie uma conta gratuita

### 1.2 Criar repositório no GitHub
1. Clique no "+" no canto superior direito
2. Clique em "New repository"
3. Nome: `AI-Market-Analyzer`
4. Deixe public
5. Clique em "Create repository"
6. Clique em "uploading an existing file"
7. Arraste TODOS os arquivos da pasta do projeto
8. Clique em "Commit changes"

### 1.3 Criar conta no Railway
1. Acesse https://railway.app
2. Clique em "Login" e entre com GitHub
3. Clique em "New Project"
4. Clique em "Deploy from GitHub repo"
5. Selecione seu repositório `AI-Market-Analyzer`

### 1.4 Configurar variáveis de ambiente
No painel do Railway, vá em "Variables" e adicione:

```
AUTH_SECRET_KEY=xlBv21gympDb99Im5u_pOsO2nAnlpeYVadERD8SYOcXyk_v8RmjLPv6z2HzYwYv5s1MSC5Ly-yVp-eYkUYZehA
AUTH_TOKEN_EXPIRE_MINUTES=1440
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
MT5_LOGIN=0
MT5_SERVER=
MT5_PASSWORD=
```

### 1.5 Aguardar deploy
- Railway vai buildar e deployar automaticamente
- Clique em "Settings" para ver a URL
- Será algo como: `ai-market-analyzer.up.railway.app`
- **Anote essa URL!**

### 1.6 Testar
- Abra o navegador do celular
- Acesse `https://ai-market-analyzer.up.railway.app`
- Faça login com admin / admin123
- Se funcionar, o backend está online!

---

## PASSO 2: Baixar o APK

### 2.1 Acessar o GitHub Actions
1. Vá ao seu repositório no GitHub
2. Clique na aba "Actions"
3. Clique em "Build Android APK"
4. Clique em "Run workflow"
5. Aguarde o build completar (~5 min)
6. Quando terminar, clique na última execução
7. Em "Artifacts", baixe `AI-Market-Analyzer-debug`

### 2.2 Instalar no celular
1. Transfira o arquivo APK para o celular (WhatsApp, email, USB, etc.)
2. No celular, toque no arquivo APK
3. Se pedir, ative "Fontes desconhecidas" nas configurações
4. Clique em "Instalar"
5. Aguarde instalar
6. Clique em "Abrir"

### 2.3 Configurar URL do servidor
**IMPORTANTE:** Antes de usar, edite o arquivo `strings.xml` no repositório:

1. No GitHub, vá em `android-app/app/src/main/res/values/strings.xml`
2. Clique no ícone de editar (lápis)
3. Troque a URL pelo endereço do seu Railway:
```xml
<string name="server_url">https://SEU-APP.up.railway.app</string>
4. Clique em "Commit changes"
5. O GitHub Actions vai rebuildar automaticamente
6. Baixe o APK novamente

---

## PASSO 3: Usar o App

1. Abra o app "AI Market Analyzer"
2. Aguarde o splash screen
3. Faça login:
   - Usuário: `admin`
   - Senha: `admin123`
4. O dashboard aparece com dados em tempo real!
5. Puxe para baixo para atualizar
6. Use o botão voltar para navegar

---

## SOLUÇÃO DE PROBLEMAS

### App não conecta
- Verifique se o Railway está rodando (painel>Show Logs)
- Teste a URL no navegador do celular
- Verifique se a URL está correta no `strings.xml`

### APK não instala
- Ative "Fontes desconhecidas" nas configurações
- Android 8+: Configurações > Apps > Desconhecidos > Permita seu navegador

### Build do GitHub Actions falha
- Verifique se o código foi commitado corretamente
- Vá em Actions > clique na execução > veja o erro
- Corrija o erro e faça push novamente

### Login não funciona
- Senha padrão: `admin123`
- Se esqueceu, delete o arquivo `users.json` no Railway e reinicie

---

## CUSTO TOTAL

| Item | Custo |
|------|-------|
| GitHub | Gratuito |
| Railway | Gratuito (500h/mês) |
| APK | Gratuito |
| **Total** | **Gratuito** |

---

## LINKS ÚTEIS

- GitHub: https://github.com
- Railway: https://railway.app
- Android Studio: https://developer.android.com/studio (opcional)

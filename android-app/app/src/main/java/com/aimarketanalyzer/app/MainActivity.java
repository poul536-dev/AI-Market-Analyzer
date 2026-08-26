package com.aimarketanalyzer.app;

import android.annotation.SuppressLint;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout errorLayout;
    private SwipeRefreshLayout swipeRefresh;
    private String serverUrl;
    private SharedPreferences prefs;

    private static final String PREFS_NAME = "AIMarketAnalyzer";
    private static final String KEY_SERVER_URL = "server_url";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        );

        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        serverUrl = prefs.getString(KEY_SERVER_URL, getString(R.string.server_url));

        webView = findViewById(R.id.webview);
        progressBar = findViewById(R.id.progress_bar);
        errorLayout = findViewById(R.id.error_layout);
        swipeRefresh = findViewById(R.id.swipe_refresh);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setAllowFileAccess(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                progressBar.setVisibility(View.VISIBLE);
                errorLayout.setVisibility(View.GONE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request.isForMainFrame()) {
                    progressBar.setVisibility(View.GONE);
                    swipeRefresh.setRefreshing(false);
                    showError();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress < 100) {
                    progressBar.setVisibility(View.VISIBLE);
                } else {
                    progressBar.setVisibility(View.GONE);
                }
            }
        });

        swipeRefresh.setColorSchemeColors(
            getResources().getColor(R.color.accent, getTheme())
        );
        swipeRefresh.setOnRefreshListener(() -> {
            if (isNetworkAvailable()) {
                webView.reload();
            } else {
                swipeRefresh.setRefreshing(false);
                showError();
            }
        });

        Button retryButton = findViewById(R.id.retry_button);
        retryButton.setOnClickListener(v -> {
            if (isNetworkAvailable()) {
                errorLayout.setVisibility(View.GONE);
                webView.loadUrl(serverUrl);
            }
        });

        webView.setOnLongClickListener(v -> {
            showSettingsDialog();
            return true;
        });
        webView.setLongClickable(true);

        if (isNetworkAvailable()) {
            webView.loadUrl(serverUrl);
        } else {
            showError();
        }
    }

    private void showSettingsDialog() {
        String[] options = {
            "Cloud (Railway) - Sempre disponivel",
            "Local (WiFi) - MT5 em tempo real",
            "URL personalizada"
        };

        new AlertDialog.Builder(this, R.style.Theme_AIMarketAnalyzer)
            .setTitle("Configurar Servidor")
            .setItems(options, (dialog, which) -> {
                switch (which) {
                    case 0:
                        setServerUrl("https://ai-market-analyzer-production.up.railway.app");
                        break;
                    case 1:
                        setServerUrl("http://192.168.15.8:8000");
                        break;
                    case 2:
                        showCustomUrlDialog();
                        break;
                }
            })
            .show();
    }

    private void showCustomUrlDialog() {
        EditText input = new EditText(this);
        input.setText(serverUrl);
        input.setHint("http://192.168.x.x:8000");

        new AlertDialog.Builder(this, R.style.Theme_AIMarketAnalyzer)
            .setTitle("URL do Servidor")
            .setView(input)
            .setPositiveButton("Salvar", (dialog, which) -> {
                String url = input.getText().toString().trim();
                if (!url.isEmpty()) {
                    setServerUrl(url);
                }
            })
            .setNegativeButton("Cancelar", null)
            .show();
    }

    private void setServerUrl(String url) {
        serverUrl = url;
        prefs.edit().putString(KEY_SERVER_URL, url).apply();
        Toast.makeText(this, "Servidor: " + url, Toast.LENGTH_SHORT).show();
        if (isNetworkAvailable()) {
            webView.loadUrl(serverUrl);
        }
    }

    private void showError() {
        errorLayout.setVisibility(View.VISIBLE);
        webView.setVisibility(View.GONE);
    }

    private boolean isNetworkAvailable() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
        if (cm != null) {
            NetworkInfo info = cm.getActiveNetworkInfo();
            return info != null && info.isConnected();
        }
        return false;
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }

        if (keyCode == KeyEvent.KEYCODE_BACK) {
            moveTaskToBack(true);
            return true;
        }

        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}

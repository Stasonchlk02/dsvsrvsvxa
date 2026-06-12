# Step 11: Установка ChromeDriver (исправленная версия)
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1) \
    && echo "Chrome version: $CHROME_VERSION" \
    && CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) \
    && echo "Chrome major version: $CHROME_MAJOR_VERSION" \
    && curl -s "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json" \
        | python3 -c "import sys, json; data=json.load(sys.stdin); \
            downloads = data['channels']['Stable']['downloads'].get('chromedriver', []); \
            url = next((d['url'] for d in downloads if d['platform']=='linux64'), None); \
            print(url) if url else sys.exit(1)" \
        | xargs -r wget -q -O /tmp/chromedriver.zip \
    && if [ ! -s /tmp/chromedriver.zip ]; then \
        echo "Fallback: trying direct download for version $CHROME_VERSION"; \
        wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" \
            -O /tmp/chromedriver.zip; \
    fi \
    && if file /tmp/chromedriver.zip | grep -q 'Zip archive'; then \
        unzip -q /tmp/chromedriver.zip -d /tmp/ && \
        find /tmp -name 'chromedriver' -type f -executable -exec mv {} /usr/local/bin/chromedriver \; && \
        chmod +x /usr/local/bin/chromedriver && \
        rm -rf /tmp/chromedriver* && \
        echo "✅ ChromeDriver installed successfully: $(chromedriver --version)"; \
    else \
        echo "❌ Failed to download ChromeDriver - check network or version" && exit 1; \
    fi

# AstraMars OS: прокси для терминала. Управляется командой astramars-proxy.
# Каждое новое окно терминала берёт актуальное состояние прокси.
_am_proxy_file=/etc/environment.d/50-astramars-proxy.conf
if [ -r "$_am_proxy_file" ]; then
    while IFS='=' read -r _am_k _am_v; do
        case "$_am_k" in
            http_proxy|https_proxy|HTTP_PROXY|HTTPS_PROXY|no_proxy|NO_PROXY) export "$_am_k=$_am_v" ;;
        esac
    done < "$_am_proxy_file"
else
    # Прокси выключен: убираем только наши локальные значения, чужие не трогаем
    case "${http_proxy:-}" in
        http://127.0.0.1:*) unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY ;;
    esac
fi
unset _am_proxy_file _am_k _am_v

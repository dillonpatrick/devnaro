FROM archlinux:latest

# 1. Atualiza o sistema e instala ferramentas essenciais e pacotes de plugins do Zsh
RUN pacman -Syu --noconfirm && pacman -S --noconfirm \
    zsh \
    git \
    curl \
    nano \
    sudo \
    base-devel \
    python \
    python-pip \
    terraform \
    zsh-autosuggestions \
    zsh-syntax-highlighting \
    && rm -rf /var/cache/pacman/pkg/*

# 2. Argumentos para sincronização de usuário e do grupo Docker do host (GID 966)
ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000
ARG DOCKER_GID

# Cria o grupo do usuário apenas se ele ainda não existir
RUN if ! getent group $USER_GID > /dev/null; then \
        groupadd --gid $USER_GID $USERNAME; \
    fi

# Cria o usuário mapeando o UID/GID e configurando o sudo sem senha
RUN if ! getent passwd $USER_UID > /dev/null; then \
        useradd --uid $USER_UID --gid $USER_GID -m $USERNAME; \
    fi \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Cria o grupo do Docker para o container corresponder ao socket do host
RUN groupadd -g $DOCKER_GID docker_host || groupadd docker_host \
    && usermod -aG docker_host $USERNAME \
    && usermod -aG wheel $USERNAME

USER $USERNAME
WORKDIR /home/$USERNAME

# 3. Instala o uv (gerenciador de Python) para o usuário
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/$USERNAME/.local/bin:$PATH"

# 4. Instala o Oh My Zsh de forma não interativa
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" --unattended

# 5. Ativa os plugins no arquivo .zshrc do usuário
RUN sed -i 's/plugins=(git)/plugins=(git zsh-autosuggestions zsh-syntax-highlighting docker terraform uv)/g' /home/$USERNAME/.zshrc

# Define o Zsh como o shell padrão do container
CMD ["zsh"]
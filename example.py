import asyncio
from wordpress_agent import WordPressAgent
from woocommerce_agent import WooCommerceAgent

async def main():
    # Inicializar el agente de WordPress
    wp_agent = WordPressAgent(
        site_url="https://www.empacame.com",
        username="nodo",
        app_password="WNNDZ$BEPedTga1IR*34BK@4"
    )
    
    # Inicializar el agente de WooCommerce
    wc_agent = WooCommerceAgent(
        site_url="https://www.empacame.com",
        consumer_key="ck_af20e57fc3bc6ec9ae5f23fd29e0eb2e0b4db566",
        consumer_secret="cs_85e29dccbb6ef59c1426a6b3fd6f81875ab000da",
        username="nodo",
        app_password="WNNDZ$BEPedTga1IR*34BK@4"
    )
    
    # Ejemplo: Crear un nuevo producto
    product = await wc_agent.create_product(
        name="Producto de ejemplo",
        description="Descripción del producto",
        price=99.99,
        categories=[1],  # IDs de categorías
        images=["https://ejemplo.com/imagen.jpg"]
    )
    
    # Ejemplo: Obtener sugerencias de contenido
    suggestions = await wc_agent.get_product_suggestions(product['id'])
    
    # Ejemplo: Crear un post relacionado
    post = await wc_agent.create_product_post(product['id'])
    
    # Ejemplo: Crear un post independiente
    wp_post = wp_agent.create_post(
        title="Nuevo artículo",
        content="Contenido del artículo",
        status="publish"
    )

if __name__ == "__main__":
    asyncio.run(main()) 
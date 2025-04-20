import asyncio
import logging
from typing import Dict, List, Optional
import requests
import json
from datetime import datetime
import urllib3
import os
import base64

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WooCommerceAgent:
    """
    Agente especializado en la gestión de productos y categorías de WooCommerce.
    """
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Inicializa el agente de WooCommerce.
        
        Args:
            site_url: URL del sitio WordPress
            consumer_key: Clave de consumidor de WooCommerce
            consumer_secret: Secreto de consumidor de WooCommerce
        """
        self.site_url = site_url.rstrip('/')
        self.wc_api_url = f"{self.site_url}/wp-json/wc/v3"
        self.wp_api_url = f"{self.site_url}/wp-json/wp/v2"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.logger = logging.getLogger(__name__)
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        # Verificar conexión inicial
        self._verify_connection()
        
    def _verify_connection(self):
        """Verifica la conexión con la API de WooCommerce."""
        try:
            # Primero intentamos una operación de lectura
            endpoint = f"{self.wc_api_url}/products"
            response = requests.get(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=self._get_wc_auth_params(),
                verify=False
            )
            
            if response.status_code == 401:
                self.logger.error("Error de autenticación: La clave API no tiene permisos de lectura")
                self.logger.error("Por favor, verifica que las credenciales sean correctas y tengan los permisos necesarios")
                raise Exception("Error de autenticación")
                
            response.raise_for_status()
            self.logger.info("Conexión con WooCommerce API verificada correctamente")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error verificando conexión con WooCommerce API: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            raise
        
    def _get_wc_auth_headers(self) -> Dict:
        """Genera los headers de autenticación para la API de WooCommerce."""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _get_wc_auth_params(self) -> Dict:
        """Genera los parámetros de autenticación para la API de WooCommerce."""
        return {
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret
        }
    
    async def upload_image(self, image_path: str) -> Dict:
        """Sube una imagen a WordPress y devuelve su ID."""
        try:
            # Verificar que el archivo existe
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"El archivo {image_path} no existe")
            
            # Leer el archivo y codificarlo en base64
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Preparar los datos para la subida
            filename = os.path.basename(image_path)
            data = {
                'file': image_data,
                'filename': filename
            }
            
            # Subir la imagen
            response = requests.post(
                f"{self.wp_api_url}/media",
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                auth=(self.consumer_key, self.consumer_secret),
                json=data,
                verify=False
            )
            
            response.raise_for_status()
            image_info = response.json()
            self.logger.info(f"Imagen subida exitosamente con ID: {image_info['id']}")
            return image_info
            
        except Exception as e:
            self.logger.error(f"Error subiendo imagen: {e}")
            return {}

    async def create_product(self, name: str, description: str, price: float, 
                           categories: List[int] = None, images: List[str] = None,
                           stock_quantity: int = None, sku: str = None) -> Dict:
        """Crea un nuevo producto en WooCommerce."""
        endpoint = f"{self.wc_api_url}/products"
        
        # Procesar imágenes si se proporcionan
        image_data = []
        if images:
            for image_path in images:
                image_info = await self.upload_image(image_path)
                if image_info:
                    image_data.append({
                        'id': image_info['id'],
                        'src': image_info['source_url']
                    })
        
        data = {
            'name': name,
            'description': description,
            'regular_price': str(price),
            'status': 'publish',
            'categories': [{'id': cat_id} for cat_id in (categories or [])],
            'images': image_data
        }
        
        if stock_quantity is not None:
            data['manage_stock'] = True
            data['stock_quantity'] = stock_quantity
            
        if sku:
            data['sku'] = sku
        
        try:
            response = requests.post(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=self._get_wc_auth_params(),
                json=data,
                verify=False
            )
            response.raise_for_status()
            product = response.json()
            self.logger.info(f"Producto creado con ID: {product['id']}")
            return product
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error creando producto: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return {}

    async def update_product(self, product_id: int, data: Dict) -> Dict:
        """Actualiza un producto existente."""
        endpoint = f"{self.wc_api_url}/products/{product_id}"
        
        try:
            response = requests.put(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=self._get_wc_auth_params(),
                json=data,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error actualizando producto {product_id}: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return {}
    
    async def delete_product(self, product_id: int, force: bool = True) -> bool:
        """Elimina un producto."""
        endpoint = f"{self.wc_api_url}/products/{product_id}"
        params = self._get_wc_auth_params()
        params['force'] = force
        
        try:
            response = requests.delete(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=params,
                verify=False
            )
            response.raise_for_status()
            self.logger.info(f"Producto {product_id} eliminado correctamente")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error eliminando producto {product_id}: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return False
    
    async def get_products(self, per_page: int = 10) -> List[Dict]:
        """Obtiene los productos de la tienda."""
        endpoint = f"{self.wc_api_url}/products"
        params = self._get_wc_auth_params()
        params['per_page'] = per_page
        
        try:
            response = requests.get(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=params,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error obteniendo productos: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return []
    
    async def create_category(self, name: str, description: str = None, parent: int = None) -> Dict:
        """Crea una nueva categoría."""
        endpoint = f"{self.wc_api_url}/products/categories"
        data = {
            'name': name,
            'description': description or '',
        }
        
        if parent:
            data['parent'] = parent
            
        try:
            response = requests.post(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=self._get_wc_auth_params(),
                json=data,
                verify=False
            )
            response.raise_for_status()
            category = response.json()
            self.logger.info(f"Categoría creada con ID: {category['id']}")
            return category
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error creando categoría: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return {}
    
    async def update_category(self, category_id: int, data: Dict) -> Dict:
        """Actualiza una categoría existente."""
        endpoint = f"{self.wc_api_url}/products/categories/{category_id}"
        
        try:
            response = requests.put(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=self._get_wc_auth_params(),
                json=data,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error actualizando categoría {category_id}: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return {}
    
    async def delete_category(self, category_id: int, force: bool = True) -> bool:
        """Elimina una categoría."""
        endpoint = f"{self.wc_api_url}/products/categories/{category_id}"
        params = self._get_wc_auth_params()
        params['force'] = force
        
        try:
            response = requests.delete(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=params,
                verify=False
            )
            response.raise_for_status()
            self.logger.info(f"Categoría {category_id} eliminada correctamente")
            return True
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error eliminando categoría {category_id}: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return False
    
    async def get_categories(self, per_page: int = 10) -> List[Dict]:
        """Obtiene las categorías de la tienda."""
        endpoint = f"{self.wc_api_url}/products/categories"
        params = self._get_wc_auth_params()
        params['per_page'] = per_page
        
        try:
            response = requests.get(
                endpoint,
                headers=self._get_wc_auth_headers(),
                params=params,
                verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error obteniendo categorías: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return []

    async def update_product_images(self, product_id: int, image_paths: List[str]) -> Dict:
        """Actualiza las imágenes de un producto existente."""
        # Procesar nuevas imágenes
        image_data = []
        for image_path in image_paths:
            image_info = await self.upload_image(image_path)
            if image_info:
                image_data.append({
                    'id': image_info['id'],
                    'src': image_info['source_url']
                })
        
        if not image_data:
            return {}
            
        data = {'images': image_data}
        
        try:
            response = requests.put(
                f"{self.wc_api_url}/products/{product_id}",
                headers=self._get_wc_auth_headers(),
                params=self._get_wc_auth_params(),
                json=data,
                verify=False
            )
            response.raise_for_status()
            product = response.json()
            self.logger.info(f"Imágenes actualizadas para el producto {product_id}")
            return product
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error actualizando imágenes: {e}")
            if hasattr(e.response, 'text'):
                self.logger.error(f"Respuesta del servidor: {e.response.text}")
            return {}

async def interactive_menu(agent: WooCommerceAgent):
    """Menú interactivo para gestionar productos y categorías."""
    while True:
        print("\n=== Menú de Gestión de WooCommerce ===")
        print("1. Listar productos")
        print("2. Listar categorías")
        print("3. Crear nuevo producto")
        print("4. Crear nueva categoría")
        print("5. Actualizar producto")
        print("6. Actualizar categoría")
        print("7. Eliminar producto")
        print("8. Eliminar categoría")
        print("9. Agregar imágenes a producto")
        print("0. Salir")
        
        choice = input("\nSelecciona una opción (0-9): ")
        
        if choice == "0":
            print("Saliendo del programa...")
            break
            
        elif choice == "1":
            products = await agent.get_products()
            print("\nProductos en la tienda:")
            for p in products:
                print(f"- {p['name']} (ID: {p['id']}, Precio: ${p['price']}, Stock: {p.get('stock_quantity', 'N/A')})")
                if p.get('images'):
                    print(f"  Imágenes: {len(p['images'])}")
                
        elif choice == "2":
            categories = await agent.get_categories()
            print("\nCategorías en la tienda:")
            for c in categories:
                print(f"- {c['name']} (ID: {c['id']})")
                
        elif choice == "3":
            name = input("Nombre del producto: ")
            description = input("Descripción: ")
            price = float(input("Precio: "))
            stock = int(input("Cantidad en stock: "))
            sku = input("SKU: ")
            
            # Manejo de imágenes
            images = []
            while True:
                image_path = input("\nRuta de la imagen (deja vacío para terminar): ")
                if not image_path:
                    break
                if os.path.exists(image_path):
                    images.append(image_path)
                else:
                    print("¡El archivo no existe!")
            
            # Mostrar categorías disponibles
            categories = await agent.get_categories()
            print("\nCategorías disponibles:")
            for c in categories:
                print(f"{c['id']}: {c['name']}")
            category_ids = [int(id) for id in input("IDs de categorías (separados por comas): ").split(",")]
            
            product = await agent.create_product(
                name=name,
                description=description,
                price=price,
                categories=category_ids,
                images=images,
                stock_quantity=stock,
                sku=sku
            )
            if product:
                print(f"\nProducto creado exitosamente:")
                print(f"ID: {product['id']}")
                print(f"Nombre: {product['name']}")
                print(f"Precio: ${product['price']}")
                print(f"Stock: {product['stock_quantity']}")
                print(f"SKU: {product['sku']}")
                if product.get('images'):
                    print(f"Imágenes: {len(product['images'])}")
                
        elif choice == "4":
            name = input("Nombre de la categoría: ")
            description = input("Descripción (opcional): ")
            
            # Mostrar categorías disponibles para parent
            categories = await agent.get_categories()
            print("\nCategorías disponibles para parent:")
            print("0: Sin parent")
            for c in categories:
                print(f"{c['id']}: {c['name']}")
            parent_id = int(input("ID de categoría parent (0 para ninguna): "))
            
            category = await agent.create_category(
                name=name,
                description=description,
                parent=parent_id if parent_id > 0 else None
            )
            if category:
                print(f"\nCategoría creada exitosamente:")
                print(f"ID: {category['id']}")
                print(f"Nombre: {category['name']}")
                
        elif choice == "5":
            product_id = int(input("ID del producto a actualizar: "))
            print("\nDeja en blanco los campos que no quieras actualizar")
            name = input("Nuevo nombre: ")
            description = input("Nueva descripción: ")
            price = input("Nuevo precio: ")
            stock = input("Nueva cantidad en stock: ")
            
            data = {}
            if name: data['name'] = name
            if description: data['description'] = description
            if price: data['regular_price'] = str(float(price))
            if stock: 
                data['manage_stock'] = True
                data['stock_quantity'] = int(stock)
            
            if data:
                product = await agent.update_product(product_id, data)
                if product:
                    print(f"\nProducto actualizado exitosamente:")
                    print(f"ID: {product['id']}")
                    print(f"Nombre: {product['name']}")
                    print(f"Precio: ${product['price']}")
                    print(f"Stock: {product['stock_quantity']}")
            else:
                print("No se especificaron cambios para realizar")
                
        elif choice == "6":
            category_id = int(input("ID de la categoría a actualizar: "))
            print("\nDeja en blanco los campos que no quieras actualizar")
            name = input("Nuevo nombre: ")
            description = input("Nueva descripción: ")
            
            data = {}
            if name: data['name'] = name
            if description: data['description'] = description
            
            if data:
                category = await agent.update_category(category_id, data)
                if category:
                    print(f"\nCategoría actualizada exitosamente:")
                    print(f"ID: {category['id']}")
                    print(f"Nombre: {category['name']}")
            else:
                print("No se especificaron cambios para realizar")
                
        elif choice == "7":
            product_id = int(input("ID del producto a eliminar: "))
            if await agent.delete_product(product_id):
                print("Producto eliminado exitosamente")
                
        elif choice == "8":
            category_id = int(input("ID de la categoría a eliminar: "))
            if await agent.delete_category(category_id):
                print("Categoría eliminada exitosamente")
                
        elif choice == "9":
            product_id = int(input("ID del producto al que agregar imágenes: "))
            images = []
            while True:
                image_path = input("\nRuta de la imagen (deja vacío para terminar): ")
                if not image_path:
                    break
                if os.path.exists(image_path):
                    images.append(image_path)
                else:
                    print("¡El archivo no existe!")
            
            if images:
                product = await agent.update_product_images(product_id, images)
                if product:
                    print(f"\nImágenes agregadas exitosamente al producto {product_id}")
                    print(f"Total de imágenes: {len(product.get('images', []))}")
            else:
                print("No se especificaron imágenes para agregar")
                
        else:
            print("Opción no válida. Por favor, selecciona una opción del 0 al 9.")

async def main():
    # Inicializar el agente con las nuevas credenciales
    agent = WooCommerceAgent(
        site_url="https://www.empacame.com",
        consumer_key="ck_87cf283b38d634f959af0894b7a0de60482a92f0",
        consumer_secret="cs_8212b5a647321df8f8a976d4be31cc2b7ea86976"
    )
    
    # Iniciar el menú interactivo
    await interactive_menu(agent)

# --- Ejecución ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] AGENT: Interrupción recibida. Cerrando agente...")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] AGENT: Agente detenido.")
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("Por favor, verifica que las credenciales sean correctas y tengan los permisos necesarios.") 
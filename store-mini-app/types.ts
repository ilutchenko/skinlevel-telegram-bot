
export type ProductStatus = 'in_stock' | 'out_of_stock' | 'hidden';

export interface Product {
    id: number;
    name: string;
    description: string;
    category: string;
    volume: string;
    price: number;
    status: ProductStatus;
    image: string;
}

export interface CartItem {
    product: Product;
    quantity: number;
}
